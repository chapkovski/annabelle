from . import models
from ._builtin import Page, WaitPage
from otree.api import Currency as c, currency_range
# from otree.api import models as m
from .models import Constants, Player
from otree.common import safe_json
from otree.views.abstract import get_view_from_url
from otree.api import widgets
import random
import itertools
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.template.response import TemplateResponse
from django.core.urlresolvers import reverse
from otree.models_concrete import (
    PageCompletion, CompletedSubsessionWaitPage,
    CompletedGroupWaitPage, PageTimeout, UndefinedFormModel,
    ParticipantLockModel, GlobalLockModel, ParticipantToPlayerLookup
)
from otree.models import Participant
import time
import channels
import json

def vars_for_all_templates(self):
    return {'index_in_pages': self._index_in_pages, }

class CustomPage(Page):
    timeout_seconds = 60

    def extra_is_displayed(self):
        return True

    def is_displayed(self):
        return not self.participant.vars.get('endofgame') and self.extra_is_displayed()

class MyWaitPage(WaitPage):
    def extra_is_displayed(self):
        return True

    def is_displayed(self):
        return not self.participant.vars.get('endofgame') and self.extra_is_displayed()



class CustomWaitPage(MyWaitPage):
    template_name = 'phd_simple/CustomWaitPage.html'


class StartWP(CustomWaitPage):
    group_by_arrival_time = True
    template_name = 'phd_simple/FirstWaitPage.html'

    def extra_is_displayed(self):
        return self.subsession.round_number == 1

    def vars_for_template(self):
        now = time.time()
        if not self.player.startwp_timer_set:
            self.player.startwp_timer_set = True
            self.player.startwp_time = time.time()
        time_left = self.player.startwp_time + Constants.startwp_timer - now
        return {'time_left':round(time_left)}

    def dispatch(self, *args, **kwargs):
        curparticipant = Participant.objects.get(code__exact=kwargs['participant_code'])
        if self.request.method == 'POST':
            curparticipant.vars['endofgame'] = True
            curparticipant.save()
        return super().dispatch(*args, **kwargs)

    def get_players_for_group(self, waiting_players):
        endofgamers = [p for p in waiting_players if p.participant.vars.get('endofgame')]
        if endofgamers:
            return endofgamers
        slowpokes = [p.participant for p in self.subsession.get_players()
                     if p.participant._index_in_pages
                     <= self._index_in_pages]
        if len(slowpokes) < Constants.players_per_group:
            self.subsession.not_enough_players = True

        if len(waiting_players) == Constants.players_per_group:
            return waiting_players

    def is_displayed(self):
        return self.round_number == 1



class Introduction(CustomPage):
    form_model = models.Player
    form_fields = ['question_1', 'question_2']
    timeout_seconds = 120
    timeout_submission = {'question_1':1,
                          'question_2':2}

    def question_1_error_message(self, value):
        if not (value == 1):
            return 'This is the wrong answer. The correct answer is >>It will be shared equally between all players at the end of the game<<. Please submit the correct answer.'

    def question_2_error_message(self, value):
        if not (value == 2):
            return 'This is the wrong answer. The correct answer is >>It gets converted into USD at the end of the game<<. Please submit the correct answer.'

    def extra_is_displayed(self):
        return self.round_number == 1


    def vars_for_template(self):
        return {
            'politician': self.player.id_in_group == 1,
            'bureaucrat': self.player.id_in_group == 2,
            'citizen': self.player.id_in_group == 3
        }

    def before_next_page(self):
        self.player.check_comprehension()

        waiting_pages = ['BonusWaitPage']

        wp_sec_in_sec = sum(PageCompletion.objects.filter(participant=self.player.participant,
                                                          page_name__in=waiting_pages).values_list('seconds_on_page',
                                                                                                   flat=True))

        self.player.tot_seconds_waited = round(wp_sec_in_sec, 2)
        self.player.moneyfortime = round(self.player.tot_seconds_waited /2000,2) * 1000

        treatment=itertools.cycle(['nominal', 'specific', 'agenda'])
        for g in self.subsession.get_groups():
            g.treatment = next(treatment)
            g.badfb_cost = random.randint(1, 10)
            g.goodfb_benefit = random.randint(1, 10)
            g.monitoring_cost = random.randint(1, 10)
            g.multiplication_factor = random.randint(1, 2)

            self.participant.vars['treatment'] = g.treatment


        parti = self.request.build_absolute_uri(self.player.participant._start_url())
        self.request.session["otree"] = parti
        self.request.session.set_expiry(4838400)


class CustomWaitPage(MyWaitPage):
    template_name = 'phd_simple/CustomWaitPage.html'
    title_text = "Waiting for other players to complete their tasks. The game will continue shortly."

    def extra_is_displayed(self):
        return (self.player.id_in_group == 1 or self.player.id_in_group == 2 or self.player.id_in_group == 3)

    def after_all_players_arrive(self):
        self.group.bureau_public = Constants.budget - self.group.allocation_bureau


class WaitingRoom(MyWaitPage):
    template_name = 'phd_simple/WaitingRoom.html'

    def extra_is_displayed(self):
        return self.player.id_in_group == 4


class Polit(CustomPage):
    form_model = models.Group
    form_fields = ['allocation_pol', 'specific_given', 'nominal_given']
    timeout_submission = {'allocation_pol': 100}
    timeout_seconds = 80

    def extra_is_displayed(self):
        return self.player.id_in_group == 1

    def before_next_page(self):
        self.player.define_budget()

        if self.round_number>1:
            self.group.treatment = self.group.in_round(self.round_number - 1).treatment
            self.group.badfb_cost = self.group.in_round(self.round_number - 1).badfb_cost
            self.group.goodfb_benefit = self.group.in_round(self.round_number - 1).goodfb_benefit
            self.group.monitoring_cost = self.group.in_round(self.round_number - 1).monitoring_cost
            self.group.multiplication_factor = self.group.in_round(self.round_number - 1).multiplication_factor

    def vars_for_template(self):
        if self.round_number > 1:
            return {
                'correct_spec': ((self.round_number >= 8) and
                                 (self.group.treatment == 'specific' or self.group.treatment == 'agenda')),
                'correct_nom': ((self.round_number >= 8) and
                                self.group.treatment == 'nominal'),
                'player_now': self.player.in_round(self.round_number).role(),
                'player_previous': self.player.in_round(self.round_number - 1).role(),
                'current_round_else': self.round_number,
                'visible': self.round_number >= 8,
                'bureau_alloc': self.group.in_round(self.round_number - 1).allocation_bureau,
                'bureau_self': self.group.in_round(self.round_number - 1).slack_bureau,
                'election_round': self.round_number == 6 or self.round_number == 8 or self.round_number == 10 or self.round_number == 12
            }
        else:
            return {
                'correct_spec': ((self.round_number >= 8) and
                                 (self.group.treatment == 'specific' or self.group.treatment == 'agenda')),
                'correct_nom': ((self.round_number >= 8) and
                                self.group.treatment == 'nominal'),
                'player_now': self.player.in_round(self.round_number).role(),
                'current_round_1': self.round_number,
                'visible': self.round_number >= 8
            }

class PolitTwo(CustomPage):
    form_model = models.Group
    form_fields = ['slack_pol']
    timeout_submission = {'slack_pol': 0}
    timeout_seconds = 80

    def extra_is_displayed(self):
        return self.player.id_in_group == 1

    def slack_pol_choices(self):
        return currency_range(0, self.player.slack_budget, 1)

    def before_next_page(self):
        self.group.common_pool()

    def vars_for_template(self):
        if self.round_number>1:
            return {
                'visible': self.round_number >= 8,
                'bureau_alloc': self.group.in_round(self.round_number - 1).allocation_bureau,
                'bureau_self': self.group.in_round(self.round_number - 1).slack_bureau
            }

class Bureau(CustomPage):
    form_model = models.Group
    form_fields = ['allocation_bureau', 'agenda_feedback']
    timeout_submission = {'allocation_bureau': 0}
    timeout_seconds = 80

    def extra_is_displayed(self):
        return self.player.id_in_group == 2

    def allocation_bureau_choices(self):
        return currency_range(0, self.group.allocation_pol, 1)

    def before_next_page(self):
        self.player.define_budget()
        for p in self.group.get_players():
            p.payoff=0

    def vars_for_template(self):
        if self.round_number > 1:
            return {
                'correct_spec_only': (self.round_number >= 10 and
                                      self.group.treatment == 'specific'),
                'correct_agenda': (self.round_number >= 10 and
                                   self.group.treatment == 'agenda'),
                'correct_nom': (self.round_number >= 10 and
                                self.group.treatment == 'nominal'),
                'correct_spec_only_c': (self.round_number >= 10 and
                                      self.group.treatment == 'specific'),
                'correct_agenda_c': (self.round_number >= 10 and
                                   self.group.treatment == 'agenda'),
                'correct_nom_c': (self.round_number >= 10 and self.group.treatment == 'nominal'),
                'total_citi': Constants.budget * self.round_number - self.group.allocation_bureau,
                'specific_1': self.group.specific_given == 1,
                'specific_1_c': self.group.in_round(self.round_number - 1).specific_given_c == 1,
                'specific_2': self.group.specific_given == 2,
                'specific_2_c': self.group.in_round(self.round_number - 1).specific_given_c == 2,
                'specific_3': self.group.specific_given == 3,
                'specific_3_c': self.group.in_round(self.round_number - 1).specific_given_c == 3,
                'nominal_1': self.group.nominal_given == 1,
                'nominal_1_c': self.group.in_round(self.round_number - 1).nominal_given_c == 1,
                'nominal_2': self.group.nominal_given == 2,
                'nominal_2_c': self.group.in_round(self.round_number - 1).nominal_given_c == 2,
                'nominal_3': self.group.nominal_given == 3,
                'nominal_3_c': self.group.in_round(self.round_number - 1).nominal_given_c == 3,
                'previous_round': self.player.round_number - 1,
                'common_pool_p': Constants.budget - self.group.allocation_pol,
                'visible': self.round_number >= 8
            }

class BureauTwo(CustomPage):
    form_model = models.Group
    form_fields = ['slack_bureau']
    timeout_seconds = 80
    timeout_submission = {'slack_bureau': 0}

    def extra_is_displayed(self):
        return self.player.id_in_group == 2

    def slack_bureau_choices(self):
        return currency_range(0, self.player.slack_budget, 1)

    def before_next_page(self):
        self.group.set_payoffs()

    def vars_for_template(self):
        if self.round_number > 1:
            return {
                'visible': self.round_number >= 8
            }


class Citi(CustomPage):
    form_model = models.Group
    form_fields = ['nominal_given_c', 'specific_given_c']
    timeout_seconds = 40

    def extra_is_displayed(self):
        return self.player.id_in_group == 3

    def vars_for_template(self):
        return {
            'allocation_citizen': self.group.allocation_bureau,
            'visible': self.round_number >= 8,
            'bureau_alloc': self.group.allocation_bureau,
            'polit_alloc': self.group.allocation_pol,
            'feedback': self.round_number >= 10,
            'correct_nom2': ((self.round_number >= 10) and self.group.treatment == 'nominal'),
            'correct_spec2': ((self.round_number >= 10) and (self.group.treatment == 'specific' or self.group.treatment == 'agenda')),
            'enough_money': self.player.payoff >= self.group.monitoring_cost,
            'not_enough_money': self.player.payoff < self.group.monitoring_cost
            }

    def before_next_page(self):
        self.group.common_pool()

        if self.round_number>1 and self.round_number<12:
            self.group.in_round(self.round_number + 1).treatment = self.group.in_round(self.round_number - 1).treatment
            self.group.in_round(self.round_number + 1).badfb_cost = self.group.in_round(
                self.round_number - 1).badfb_cost
            self.group.in_round(self.round_number + 1).goodfb_benefit = self.group.in_round(
                self.round_number - 1).goodfb_benefit
            self.group.in_round(self.round_number + 1).monitoring_cost = self.group.in_round(
                self.round_number - 1).monitoring_cost
            self.group.in_round(self.round_number + 1).multiplication_factor = self.group.in_round(
                self.round_number - 1).multiplication_factor

        if self.round_number>1:
            if self.group.treatment == "specific" or self.group.treatment == "agenda":
                if self.group.in_round(self.round_number - 1).specific_given == 1:
                    self.group.benefit_pol = self.group.goodfb_benefit
                    self.group.benefit_c = self.group.goodfb_benefit
                elif self.group.in_round(self.group.round_number - 1).specific_given == 3:
                    self.group.cost_pol = self.group.badfb_cost
                    self.group.cost_c = self.group.badfb_cost
                else:
                    self.group.benefit_pol = 0
                    self.group.cost_pol = 0
                    self.group.benefit_c = 0
                    self.group.cost_c = 0
            else:
                if self.group.in_round(self.round_number - 1).nominal_given == 1:
                    self.group.benefit_pol = self.group.goodfb_benefit
                    self.group.benefit_c = self.group.goodfb_benefit
                elif self.group.in_round(self.round_number - 1).nominal_given == 3:
                    self.group.cost_pol = self.group.badfb_cost
                    self.group.cost_c = self.group.badfb_cost
                else:
                    self.group.benefit_pol = 0
                    self.group.cost_pol = 0
                    self.group.benefit_c = 0
                    self.group.cost_c = 0

            if self.group.in_round(self.round_number-1).is_elected==0 or self.group.in_round(self.round_number-1).is_elected==1:
                self.group.benefit_for_pol = self.group.in_round(self.group.round_number - 1).is_elected * self.group.goodfb_benefit
                self.group.cost_for_pol = (1 - self.group.in_round(self.group.round_number - 1).is_elected) * self.group.badfb_cost
            else:
                self.group.benefit_for_pol = 0
                self.group.cost_for_pol = 0

            self.group.cost_bureau= self.group.cost_pol + self.group.cost_c
            self.group.benefit_bureau= self.group.benefit_pol + self.group.benefit_c

            if self.group.in_round(self.round_number-1).is_elected==0:
                self.group.used_election=1
            elif self.group.in_round(self.round_number-1).is_elected==1:
                self.group.used_election=1
            else:
                self.group.used_election=0


class Citi_Elect(CustomPage):
    form_model = models.Group
    form_fields = ['is_elected']
    timeout_seconds = 20
    timeout_submission = {'is_elected': 0}

    def extra_is_displayed(self):
        return self.player.id_in_group == 3 and (self.round_number == 6 or self.round_number == 8 or self.round_number == 10)


    def vars_for_template(self):
        return {
            'allocation_citizen': self.group.allocation_bureau,
            'visible': self.round_number >=  8,
            'bureau_alloc': self.group.allocation_bureau,
            'polit_alloc': self.group.allocation_pol,
            'enough_money': self.player.payoff >= self.group.monitoring_cost,
            'not_enough_money': self.player.payoff < self.group.monitoring_cost
        }



class ResultsWaitPage(MyWaitPage):
    timeout_seconds = 60

    def extra_is_displayed(self):
        return self.round_number == 12

    def after_all_players_arrive(self):
        self.group.set_payoffs()


class ResultsSummary(CustomPage):
    timeout_seconds = 60
    form_model = models.Group

    def extra_is_displayed(self):
        return self.round_number == 12

    def vars_for_template(self):
        return {
            'total_payoff': self.player.payoff,
            'paying_round': 12,
            'participation_fee': self.session.config['participation_fee'],
            'total_payout': self.participant.payoff_plus_participation_fee
        }


class ShuffleWaitPage(MyWaitPage):
    def extra_is_displayed(self):
            return 6 < self.round_number <9

    def after_all_players_arrive(self):
        if self.group.in_round(6).is_elected == 0:
            self.group.is_elected == 0
            players = self.group.get_players()
            players[0], players[-1] = players[-1], players[0]
            self.group.set_players(players)
        else:
            self.group.is_elected == 1
            players = self.group.get_players()
            self.group.set_players(players)

class ShuffleWaitPage2(MyWaitPage):
    def extra_is_displayed(self):
            return 8<  self.round_number < 11

    def after_all_players_arrive(self):
        if self.group.in_round(8).is_elected == 0 and self.group.in_round(6).is_elected != 0:
            self.group.is_elected == 0
            players = self.group.get_players()
            players[0], players[-1] = players[-1], players[0]
            self.group.set_players(players)
        elif self.group.in_round(8).is_elected == 0 and self.group.in_round(6).is_elected == 0:
            self.group.is_elected == 0
        else:
            self.group.is_elected == 1
            players = self.group.get_players()
            self.group.set_players(players)


class ShuffleWaitPage3(MyWaitPage):
    def extra_is_displayed(self):
            return self.round_number > 10

    def after_all_players_arrive(self):
        if self.group.in_round(10).is_elected == 0 and self.group.in_round(6).is_elected != 0 and self.group.in_round(8).is_elected != 0:
            self.group.is_elected == 0
            players = self.group.get_players()
            players[0], players[-1] = players[-1], players[0]
            self.group.set_players(players)
        elif self.group.in_round(10).is_elected == 0 and self.group.in_round(6).is_elected == 0 and self.group.in_round(8).is_elected == 0:
            self.group.is_elected == 0
            players = self.group.get_players()
            players[0], players[-1] = players[-1], players[0]
            self.group.set_players(players)
        elif self.group.in_round(10).is_elected == 0 and self.group.in_round(6).is_elected == 0 and self.group.in_round(8).is_elected != 0:
            self.group.is_elected == 0
        elif self.group.in_round(10).is_elected == 0 and self.group.in_round(6).is_elected != 0 and self.group.in_round(8).is_elected == 0:
            self.group.is_elected == 0
        else:
            self.group.is_elected == 1
            players = self.group.get_players()
            self.group.set_players(players)

class GameOver(Page):
    pass

page_sequence = [
    StartWP,
    ShuffleWaitPage,
    ShuffleWaitPage2,
    ShuffleWaitPage3,
    Introduction,
    WaitPage,
    Polit,
    PolitTwo,
    CustomWaitPage,
    Bureau,
    BureauTwo,
    CustomWaitPage,
    Citi,
    Citi_Elect,
    WaitingRoom,
    ResultsWaitPage,
    ResultsSummary,
    WaitPage,
    CustomWaitPage,
    GameOver,
]
