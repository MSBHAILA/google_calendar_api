from django.shortcuts import redirect
from django.shortcuts import render

from rest_framework.decorators import api_view
from rest_framework.response import Response

import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
import os


os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

CLIENT_SECRETS_FILE = "credentials.json"

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account and requires requests to use an SSL connection and REDIRECT URL.
SCOPES = ['https://www.googleapis.com/auth/calendar',
          'https://www.googleapis.com/auth/userinfo.email',
          'https://www.googleapis.com/auth/userinfo.profile',
          'openid']
REDIRECT_URL = 'http://127.0.0.1:8000/rest/v1/calendar/redirect'
API_SERVICE_NAME = 'calendar'
API_VERSION = 'v3'


def index(request):
    return render(request, 'home.html')


@api_view(['GET'])
def GoogleCalendarInitView(request):
    # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES)

    flow.redirect_uri = REDIRECT_URL

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true')

    # Store the state so the callback can verify the auth server response.
    request.session['state'] = state

    return Response({"authorization_url": authorization_url})


@api_view(['GET'])
def GoogleCalendarRedirectView(request):
    state = request.session['state']

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
    flow.redirect_uri = REDIRECT_URL

    authorization_response = request.get_full_path()
    flow.fetch_token(authorization_response=authorization_response)

    # Save credentials back to session in case access token was refreshed.
    # ACTION ITEM: In a production app, you likely want to save these
    # credentials in a persistent database instead.
    credentials = flow.credentials
    request.session['credentials'] = credentials_to_dict(credentials)

    # Check if credentials are in session
    if 'credentials' not in request.session:
        return redirect('v1/calendar/init')

    # Load credentials from the session.
    credentials = google.oauth2.credentials.Credentials(
        **request.session['credentials'])

    service = googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, credentials=credentials)

    events_list_append = []
    page_token = None
    while True:
        events = service.events().list(calendarId='primary', pageToken=page_token).execute()
        if not events['items']:
            print('No data found.')
            return Response({"message": "No data found or user credentials invalid."})
        else:
            for events_list in events['items']:
                events_list_append.append(events_list)
            return Response({"events": events_list_append})


def credentials_to_dict(credentials):
    return {'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes}
