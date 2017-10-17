import os
from os import environ

import dj_database_url
from boto.mturk import qualification


import otree.settings

CHANNEL_ROUTING = 'phd_simple.routing.channel_routing'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# the environment variable OTREE_PRODUCTION controls whether Django runs in
# DEBUG mode. If OTREE_PRODUCTION==1, then DEBUG=False
if environ.get('OTREE_PRODUCTION') not in {None, '', '0'}:
    DEBUG = False
else:
    DEBUG = True

ADMIN_USERNAME = 'admin'

# for security, best to set admin password in an environment variable
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

# don't share this with anybody.
SECRET_KEY = 'co=ei*sk3y8cz)m)oq*8nhc66#&b20xfg%lbgies&$b=omg^x7'

DATABASES = {
    'default': dj_database_url.config(
        # Rather than hardcoding the DB parameters here,
        # it's recommended to set the DATABASE_URL environment variable.
        # This will allow you to use SQLite locally, and postgres/mysql
        # on the server
        # Examples:
        # export DATABASE_URL=postgres://USER:PASSWORD@HOST:PORT/NAME
        # export DATABASE_URL=mysql://USER:PASSWORD@HOST:PORT/NAME

        # fall back to SQLite if the DATABASE_URL env var is missing
        default='sqlite:///' + os.path.join(BASE_DIR, 'db.sqlite3')
    )
}

# AUTH_LEVEL:
# If you are launching a study and want visitors to only be able to
# play your app if you provided them with a start link, set the
# environment variable OTREE_AUTH_LEVEL to STUDY.
# If you would like to put your site online in public demo mode where
# anybody can play a demo version of your game, set OTREE_AUTH_LEVEL
# to DEMO. This will allow people to play in demo mode, but not access
# the full admin interface.

AUTH_LEVEL = environ.get('OTREE_AUTH_LEVEL')

# setting for integration with AWS Mturk
AWS_ACCESS_KEY_ID = environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = environ.get('AWS_SECRET_ACCESS_KEY')

# e.g. EUR, CAD, GBP, CHF, CNY, JPY
REAL_WORLD_CURRENCY_CODE = 'USD'
USE_POINTS = True
POINTS_CUSTOM_NAME='Rollars'


# e.g. en, de, fr, it, ja, zh-hans
# see: https://docs.djangoproject.com/en/1.9/topics/i18n/#term-language-code
LANGUAGE_CODE = 'en'

# if an app is included in SESSION_CONFIGS, you don't need to list it here
INSTALLED_APPS = ['otree',]

# ROOT_URLCONF = 'redirect.urls'

SENTRY_DSN =  'http://3f9f8ab561354449b7793766be9b96d0:a14b9f3a44f44120b708339fb47dca9e@sentry.otree.org/196'

DEMO_PAGE_INTRO_TEXT = """
oTree games
"""

# from here on are qualifications requirements for workers
# see description for requirements on Amazon Mechanical Turk website:
# http://docs.aws.amazon.com/AWSMechTurk/latest/AWSMturkAPI/ApiReference_QualificationRequirementDataStructureArticle.html
# and also in docs for boto:
# https://boto.readthedocs.org/en/latest/ref/mturk.html?highlight=mturk#module-boto.mturk.qualification

ROOM_DEFAULTS = {}

ROOMS = [
    {
        'name': 'polsci_games',
        'display_name': 'Political Science Games',
    },
]

mturk_hit_settings = {
    'keywords': ['easy', 'bonus', 'choice', 'study', 'fun', 'game'],
    'title': 'Allocation game',
   'description': 'This is a 4-player game for an academic study.',
   'frame_height': 500,
    'preview_template': 'global/MTurkPreview.html',
   'minutes_allotted_per_assignment': 30,
    'expiration_hours': 2,  # check now
    # 'grant_qualification_id': 'YOUR_QUALIFICATION_ID_HERE',# to prevent retakes
    'qualification_requirements': [
        {
            'QualificationTypeId': "00000000000000000071",
            'Comparator': "In",
            'LocaleValues': [{
                'Country': "US",
            }]
        },
                {
            'QualificationTypeId': "00000000000000000040",
            'Comparator': "GreaterThan",
            'IntegerValues':[60]
        },
        {
            'QualificationTypeId': "3QIZOA92RY5BD46NFA8L3BOWJDLPBX",
            'Comparator': "DoesNotExist",
        }
    ]
    }

# if you set a property in SESSION_CONFIG_DEFAULTS, it will be inherited by all configs
# in SESSION_CONFIGS, except those that explicitly override it.
# the session config can be accessed from methods in your apps as self.session.config,
# e.g. self.session.config['participation_fee']

SESSION_CONFIG_DEFAULTS = {
    'real_world_currency_per_point': 0.001,
    'participation_fee': 1.74,
    'doc': "Test",
    'mturk_hit_settings': mturk_hit_settings,
}

SENTRY_DSN = 'http://3f9f8ab561354449b7793766be9b96d0:a14b9f3a44f44120b708339fb47dca9e@sentry.otree.org/196'


SESSION_CONFIGS = [
    {
        'name': 'phd_game',
        'display_name': 'phd_game',
        'num_demo_participants': 8,
        'app_sequence': [ 'phd_simple', ],
        'use_browser_bots': False,
        #'treatment': 'agenda',
    },

]

# anything you put after the below line will override
# oTree's default settings. Use with caution.
otree.settings.augment_settings(globals())
