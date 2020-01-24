#!/usr/bin/env python3
__doc__ = """
"""
__date__ = '2020-01-22'
__version__ = (0,0,1)
#__all__ = ('',)

import json
import logging
import os
import re
import webbrowser
from spotify_backup import SpotifyAPI

from flask import Flask
app = Flask('spotify-dl')


def get_playlists() -> list:#{{{
    '''return list of dicts of the playlists.'''

    # Temporary file to write the playlists in JSON.
    TEMP_PLAYLISTS_FILE = '/tmp/playlists.json'

    # Download the spotify playlists by logging in using the API.
    CLIENT_ID = '5c098bcc800e45d49e476265bc9b6934'
    SCOPE = 'playlist-read-private'
    spotify = SpotifyAPI.authorize(client_id=CLIENT_ID, scope=SCOPE)

    # Get the ID of the logged in user.
    me = spotify.get('me')# {'display_name': ..., 'id': ...}

    # List all playlists and all tracks in each playlist.
    playlists = spotify.list('users/{user_id}/playlists'.format(
                            user_id=me['id']), {'limit': 50})

    # Get the tracks for each playlist.
    for playlist in playlists:
        # 'Loading playlist:  {name} ({tracks[total]} songs)'.format(**playlist)
        playlist['tracks'] = spotify.list(playlist['tracks']['href'], {'limit': 100})

    # Write the playlists to a temporary file in JSON.
    with open(TEMP_PLAYLISTS_FILE, mode='w') as f:
        json.dump(playlists, f)

    return playlists
#}}} end get_playlists


def get_track_attrs(track:dict) -> dict:#{{{
    '''returns a dict of: artist, trackname, album, from a track dict.

    where multiple artists are found for a track, only the first (primary)
    is used.
    '''
    return {'artist': track['artists'][0]['name'],
            'album': track['album']['name'],
            'trackname': track['name'],
            }
#}}} end get_track_attrs


def get_user_selections(path:str):#{{{
    '''
    '''
    #HTML_FILE_NAME = 'track_selector.html'
    #path = os.path.join(os.getcwd(), HTML_FILE_NAME)#[1:]
    webbrowser.open('file://' + path)
#}}} end get_user_selections



def write_playlist_data(playlists:dict) -> str:#{{{
    '''return the path to the playlist track_selector.html file
    after writing the track and playlist information to the file.

    Using the track_selector_template.html file, populate each file with the
    tracks and playlist information for each playlist.

    NOTE: This is a hack because I don't have an easier way of writing to and fro
    with Python and JS, yet!
    '''
    #<!--
    #  The goal is to have some buttons with each of the playlist names on them.
    #  clicking them will show a hidden list of the tracks for user selection.
    #-->
    playlist_data_path = '/tmp/track_selector.html'

    def new_form(playlist):#{{{
        '''
        # indent by 4 spaces.
        '''
        playlistname = playlist['name']
        # edit playlistname for the id to camelCase.
        form_id = re.sub(r'\s', '', re.sub(r'\W', ' ', playlistname).title())
        logging.debug(f'playlistname={playlistname!r}, form_id={form_id!r}')

        form = []
        # append a label/button to toggle hide/show each form/playlist.
        #form.append('    <label>')
        form.append('    <button type="button" id="playlist-selector-button" '
                    f'onclick=toggle_show_tracks("{form_id}");>{playlistname}</button><br>')

        # the selectAll input should also be a button that toggles selecting
        # all the checkboxes.
        form.append(f'    <form id="{form_id}">')
        form.append('      <button type="button" class="select-all-button" '
                    f'onclick=toggle_select_all("{form_id}");>Select All'
                    '</button><br>')

        # make inputs for each track in the playlist.
        for item in playlist['tracks']:
            trackstr = '{artist} {trackname}'.format(**get_track_attrs( item['track']))
            form.append('      <input type="checkbox" class="track-select-button" '
                        f'name="track" value="{trackstr}">{trackstr}<br>')

        form.append('      <br><br>')
        form.append('    </form>')
        form = '\n'.join(form)
        form += '\n' # end with a newline.
        logging.debug(f'form=\n{form}')
        return form
    #}}} end new_form


    # TODO: fix the CSS for .select-all-button and -track-select-button.
    # Why did the text become so small for the download button???
    #{{{ CSS
    track_selector_html = '''\
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
      body {
        background-color: #333333;
        color: #99ff99;
        text-align: center;
      }
      #playlist-selector-button {
        color: #99ff99;
        background-color: #666666;
      }
      #download-button {
        color: #666666;
        background-color: #99ff99;
      }
      .select-all-button {
        color: #FFFFFF;
        background-color: #000000;
      }
      .track-select-button {
        color: #000000;
        background-color: #FFFFFF;
      }
      // form {
      //   display: none;
      // }
    </style>
</head>
<body>
    <h2>Spotify Playlist Track Selector</h2>
    <br>
    <h4>Click on a playlist to show its tracks.  Choose the tracks from each
    playlist that you want to download.  Then click the download button to
    begin downloading the tracks.</h4>
    <br><br>
    <button type="button" id="download-button" onclick=download_tracks();>Download Tracks</button>
    <br><br>
    <h3>Playlists</h3>
'''#}}}

    # construct the hidden forms for each playlist.
    for playlist in playlists:
        track_selector_html += new_form(playlist)

    #{{{ javascript
    track_selector_html += '''\
    <script language="JavaScript">
      // hide all form elements.
      console.log('hiding forms!');
      var forms = document.getElementsByTagName('form');
      for (i=0;i<forms.length;i++) {
        console.log('setting display to none for form id: ' + forms[i].id);
        forms[i].style.display = "none";
      }

      function toggle_show_tracks(form_id) {
        console.log('showing tracks for ' + form_id);
        var form = document.getElementById(form_id);
        console.log('form.style.display: ' + form.style.display);

        if (form.style.display === "none") {
          console.log('setting display to block');
          form.style.display = "block";
        } else {
          console.log('setting display to none');
          form.style.display = "none";
        }
      }

      function toggle_select_all(form_id) {
        var form = document.getElementById(form_id);
        console.log('toggling select all for ' + form.id);

        // Iterate the checkbox elements in this form, and toggle their state.
        var xs = form.getElementsByClassName('track-select-button');
        console.log('found ' + xs.length + ' tracks');

        for (i=0;i<xs.length;i++) {
          var x = xs[i];
          console.log('checkbox.value: ' + x.value);
          if (x.checked === true) {
            console.log('unchecking...');
            x.checked = false;
          } else {
            console.log('checking...');
            x.checked = true;
          }
        }
      }

      function download_tracks() {
        // iterate each playlist's form and each track checkbox within
        // to determine which tracks to download. then do what with them?
        console.log('downloading...');

        var forms = document.getElementsByTagName('form');
        // iterate the forms...
        for (i=0;i<forms.length;i++) {
          console.log('setting display to none for form id: ' + forms[i].id);

          var form = forms[i];
          console.log('downloading for playlist: ' + form.id);

          // hide the form if it isn't already...
          form.style.display = "none";

          // iterate the tracks in the form...
          // and do what with them???
          var xs = form.getElementsByClassName('track-select-button');
          for (i=0;i<xs.length;i++) {
            var x = xs[i];
            if (x.checked === true) {
              console.log('downloading track: ' + x.value);
            } else {
              console.log('NOT downloading track: ' + x.value);
            }
          }
        }
      }

    </script>
</body>
</html>
'''#}}}
    with open(playlist_data_path, mode='w') as f:
        f.write(track_selector_html)
    return playlist_data_path
#}}} end write_playlist_data


@app.route('/')
def show_playlist_tracks():#{{{
    '''
    http://127.0.0.1:5000
    '''
    with open(track_selector_html_path, mode='r') as f:
        return f.read()
    #}}}


if __name__ == '__main__':
    pass
    logging.basicConfig(level='DEBUG',)

    #playlists = get_playlists()
    with open('/tmp/playlists.json', mode='r') as f:
        playlists = json.load(f)

    track_selector_html_path = write_playlist_data(playlists)
    logging.debug(f'track_selector_html_path={track_selector_html_path}')
    webbrowser.open('file://' + track_selector_html_path)



#=========================================================================={{{
    #for playlist in playlists:
    #    # each playlist is made up of track dicts, but I only want select data
    #    # from them to make up a YouTube search query.
    #    for item in playlist['tracks']:
    #        trackattrs = get_track_attrs(item['track'])
    #        # Display that each track was able to be parsed for its attributes.
    #        logging.info('album: \x1b[1;33m{album}\x1b[0m, '
    #                     'artist: \x1b[1;33m{artist}\x1b[0m, '
    #                     'trackname: \x1b[1;33m{trackname}\x1b[0m'
    #                     .format(**trackattrs))
#==========================================================================}}}
