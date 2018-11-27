"""
Django settings for EVHR project.

Generated by 'django-admin startproject' using Django 1.11.5.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.11/ref/settings/
"""

import os
import sys

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '9t8##+l+s9f*@9*+xaak5wdjm0xtd^t797lapu0y3-3wo4!k^@'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['evhr101',
                 'evhr101.atusrvm.adapt.nccs.nasa.gov',
                 'evhr102']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    'api',
    'ProcessingEngine',
    'GeoProcessingEngine',
    'EvhrEngine',
    'JobDaemon'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'EVHR.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'EVHR.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = False


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/
STATIC_URL = '/static/'

# EVHR Settings
BASE_DIRECTORY   = '/att/nobackup/rlgill/evhrDevelopmentOutput'
DOWNLOAD_DIR     = os.path.join(BASE_DIRECTORY, 'downloads')
OUTPUT_DIRECTORY = os.path.join(BASE_DIRECTORY, 'requests')
LOG_DIRECTORY    = os.path.join(BASE_DIRECTORY, 'logs')
STATIC_ROOT      = '/att/nobackup/rlgill/evhrDevelopment/EVHR/static_root'

LOGGING = {
	'version': 1,
	'disable_existing_loggers': False,
	'handlers': {
        'console': {
              'level': 'DEBUG',
              'class': 'logging.StreamHandler',
              'stream': sys.stdout,
        },
        'file': {
            'level'       : 'INFO',
            'class'       : 'logging.handlers.TimedRotatingFileHandler',
			'filename'    : os.path.join(LOG_DIRECTORY, 'evhr.log'),
            'when'        : 'midnight',
            'backupCount' : 10,
        },
        'owslib': {
              'level': 'DEBUG',
              'class': 'logging.StreamHandler',
              'stream': sys.stdout,
        },
	},
	'loggers': {
		'console': {
			'handlers' : ['console'],
			'level'    : 'DEBUG',
            'propagate': False,
		},
        'jobDaemon': {
            'handlers'  : ['console', 'file'],
            'propagate' : True,
            'level'     : 'INFO',
        },
		'owslib': {
			'handlers' : ['console'],
			'level'    : 'DEBUG',
            'propagate': True,
		},
	}
}

# WranglerProcess Settings
DAYS_UNTIL_REQUEST_PURGE = 30
DEFAULT_SCALE_IN_METERS = 30
DEM_APPLICATION = '/att/nobackup/rlgill/DgStereo/evhr/dg_stereo.sh'
FOOTPRINTS_FILE = '/att/pubrepo/NGA/INDEX/Footprints/current/newest/geodatabase/nga_inventory_canon20181004.gdb'
MAXIMUM_SCENES = 20
MERRA_END_DATE = '2017-05-31'
MERRA_START_DATE = '1980-01-01'
WORK_DIRECTORY = OUTPUT_DIRECTORY
NO_DATA_VALUE = -9999
