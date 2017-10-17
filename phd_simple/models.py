from otree.api import (
        models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer,
        Currency as c, currency_range
        )
import random

class Constants(BaseConstants):
    name_in_url='phd_simple'
    players_per_round=4
    players_per_group=4
    num_rounds=5
    budget=c(100)
    multiplication_factor=random.randint(1,2)
    startwp_timer = 15

class Player(BasePlayer):
    def role (self):
        if self.id_in_group==1:
            return 'Politician'
        if self.id_in_group==2:
            return 'Bureaucrat'
        if self.id_in_group==3:
            return 'Citizen'
        else:
            return "Waiting"
    current_wp = models.IntegerField()
    outofthegame = models.BooleanField()
    startwp_timer_set = models.BooleanField(default=False)
    startwp_time = models.PositiveIntegerField()
    age=models.PositiveIntegerField()
    gender=models.PositiveIntegerField(
            choices=[
                    [1,'Female'],
                    [2,'Male'],
                    [3,'Other'],
                    ],
            widget=widgets.RadioSelect()
            )
    income=models.PositiveIntegerField(
            choices=[
                    [1,'<£1,000/month'],
                    [2,'£1,000 - £2,000/month'],
                    [3,'£2,000 - £4,000/month'],
                    [4,'£4,000 - £6,000/month'],
                    [5,'>£6,000/month'],
                    ],
            widget=widgets.RadioSelect()
            )

    def elections(self):
        self.participant.vars['new_election'] = 0


class Group(BaseGroup):
    allocation_bureau=models.CurrencyField(
            verbose_name='How much do you want to allocate?'
             )

    allocation_pol=models.CurrencyField(
            choices=currency_range(c(0),c(100),1),
            verbose_name='How much do you want to allocate?'
            )

    public_payoff=models.CurrencyField(
            initial=c(0))

    citizen_payoff=models.CurrencyField(
            initial=c(0))

    is_elected=models.BooleanField(
           verbose_name='Do you want to re-elect the politician for another 4 rounds?'
           )

   # def set_budget(self):
     #   p2 = self.get_player_by_role('Bureaucrat')
    #    p1 = self.get_player_by_role('Politician')
   #     p2.bureau_budget= p1.allocation_pol

    def set_payoffs(self):
        politician = self.get_player_by_role('Politician')
        bureaucrat=self.get_player_by_role('Bureaucrat')
        citizen=self.get_player_by_role('Citizen')
        waiting=self.get_player_by_role('Waiting')

        for player in [politician, bureaucrat]:
            if (self.round_number==self.session.vars['paying_round']):
                player.payoff=sum([p.public_payoff for p in self.player.in_all_rounds()]) * (Constants.multiplication_factor/Constants.players_per_round)

        for player in [citizen]:
            if (self.round_number==self.session.vars['paying_round']):
                player.payoff=sum([p.public_payoff for p in self.player.in_all_rounds()]) * (Constants.multiplication_factor/Constants.players_per_round) + sum([p.citizen_payoff for p in self.player.in_all_rounds()])


class Subsession(BaseSubsession):
    not_enough_players = models.BooleanField(
        doc=""" this variable set to True when one of the players decide to
        abandon the game (because he is tired to wait), and
        there is no enough players left in the session to complete the group.
        then those remaining get the opportunity to finish the game.""",
        initial=False
    )

    def before_session_starts(self):
        paying_round= Constants.num_rounds

        for p in self.get_players():
            p.participant.vars['new_election'] = 0

        def get_player_by_id(id):
            for p in self.get_players():
                if p.id_in_subsession == id: return p

        p3=get_player_by_id(3)
        if self.round_number==4:
            for group in self.get_groups():
                players = group.get_players()
                players[0], players[-1] = players[-1], players[0]
                group.set_players(players)
