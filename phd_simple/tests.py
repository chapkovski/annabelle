from otree.api import Currency as c, currency_range
from . import views
from ._builtin import Bot
from .models import Constants
from otree.api import Submission

class PlayerBot(Bot):

    def play_round(self):
        if self.subsession.round_number==1:
            yield(views.Introduction, {'question_1':1,
                                      'question_2':2})

        if self.player.id_in_group==1:
            if self.subsession.round_number >= self.session.vars['feedback_pol_only'] and (self.group.treatment=='agenda'or self.group.treatment=='specific'):
                yield(views.Polit, {'allocation_pol':50, 'specific_given': 2})
            if self.subsession.round_number >= self.session.vars['feedback_pol_only'] and self.group.treatment=='nominal':
                yield(views.Polit, {'allocation_pol':50, 'nominal_given': 2})
            if self.subsession.round_number== self.session.vars['paying_round'] and (self.group.treatment=='agenda'or self.group.treatment=='specific'):
                yield(views.Polit, {'allocation_pol':50, 'specific_given': 2})
                yield Submission(views.ResultsSummary, check_html = False)
            if self.subsession.round_number== self.session.vars['paying_round'] and self.group.treatment=='nominal':
                yield(views.Polit, {'allocation_pol':50, 'specific_given': 2})
                yield Submission(views.ResultsSummary, check_html = False)
            else:
                yield(views.Polit, {'allocation_pol':50})

        if self.player.id_in_group==2:
            if self.subsession.round_number >= self.session.vars['feedback_pol_only'] and self.group.treatment=='agenda':
                yield(views.Bureau, {'allocation_bureau': 25,
                                     'agenda_feedback':'....'})
            if self.subsession.round_number== self.session.vars['paying_round']:
                yield(views.Bureau, {'allocation_bureau': 25,
                                     'agenda_feedback':'....'})
                yield Submission(views.ResultsSummary, check_html = False)
            else:
                yield(views.Bureau, {'allocation_bureau': 25})

        if self.player.id_in_group==3:
            if self.subsession.round_number==12 or self.subsession.round_number==16 or self.subsession.round_number==20 or self.subsession.round_number==24:
                yield(views.Citi_Elect, {'is_elected':1})
            if self.subsession.round_number==12 or self.subsession.round_number==16 or self.subsession.round_number==20 or self.subsession.round_number==24:
                yield(views.Citi_Elect, {'is_elected':1})
                yield Submission(views.ResultsSummary, check_html = False)
            else:
                yield(views.Citi)

            
            

