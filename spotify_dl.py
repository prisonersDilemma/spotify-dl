#!/usr/bin/env python3
__doc__ = """
"""
__date__ = '2020-01-22'
__version__ = (0,0,1)
#__all__ = ('',)

import json
import logging
import os
#from queue import Queue
import re
#import threading
#import webbrowser
from flask import Flask, request
from spotify_backup import SpotifyAPI
from werkzeug.exceptions import BadRequestKeyError

try:
    from .downloads import download_mp3s
except ImportError:
    from downloads import download_mp3s

app = Flask('spotify-dl')
app.config['DEBUG'] = True


# TODO: Hide the <ul> when download/submit button is clicked, if possible.
@app.route('/', methods=['GET', 'POST'])
def show_playlists() -> str:#{{{
    '''
    http://127.0.0.1:5000
    '''

    def get_playlists() -> list:#{{{
        '''return list of dicts of the playlists.'''

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

        return playlists
    #}}} end get_playlists

    def get_unordered_list(playlist):#{{{
        '''
        # indent by 4 spaces.
        '''
        # edit playlistname for the id to camelCase.
        playlistname = playlist['name']
        ul_id = re.sub(r'\s', '', re.sub(r'\W', ' ', playlistname).title())
        #logging.warning(f'playlistname={playlistname!r}, ul_id={ul_id!r}')

        ul = []
        ul.append('    <button type="button" id="playlist-selector-button" '
                    f'onclick=toggle_show_tracks("{ul_id}");>{playlistname}</button><br>')
        ul.append(f'<ul id="{ul_id}">')
        ul.append('      <button type="button" class="select-all-button" '
                    f'onclick=toggle_select_all("{ul_id}");>Select All'
                    '</button><br>')

        # make inputs for each track in the playlist.
        for item in playlist['tracks']:
            trackattrs = {'artist': item['track']['artists'][0]['name'],
                          'album': item['track']['album']['name'],
                          'trackname': item['track']['name'], }
            logging.warning(f'trackattrs: {trackattrs!r}')
            trackstr = '{artist} {trackname}'.format(**trackattrs)
            ul.append('      <li><input type="checkbox" class="track-select-button" '
                        f'name="{trackstr}" value="{trackstr}">{trackstr}<br></li>')

        ul.append('</ul>')
        return '\n'.join(ul) + '\n' #str
    #}}} end get_unordered_list


    #main
    logging.warning(f'request.method={request.method}')

    if request.method == 'GET':#{{{
        #{{{ CSS
        html = '''\
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
        </style>
    </head>
    <body>
        <h2>Spotify Playlist Track Selector</h2>
        <h4>Click on a playlist to show its tracks.  Choose the tracks from each
        playlist that you want to download.  Then click the download button to
        begin downloading the tracks.</h4>
        <h3>Playlists</h3>

        <form id="download-form" action="." method="POST">
    '''#}}}

        playlists = get_playlists()

        # construct the hidden forms for each playlist.
        for playlist in playlists:
            html += get_unordered_list(playlist)

        #{{{ javascript
        # TODO: If I'm going to use the form rather than button approach for
        # the download button, I've got to change these other JS functions that
        # manipulate the forms to exclude that one.
        html += '''\
          <br>
          <input id="download-button" type="submit" value="DOWNLOAD">
        </form>

        <script language="JavaScript">

        function toggle_lists() {//#{{{
          // Hide the lists.
          var uls = document.getElementsByTagName('ul');
          for (i=0;i<uls.length;i++) {
            var ul = uls[i];
            if (ul.style.display === "none") {
              ul.style.display = "block";
            } else {
              ul.style.display = "none";
            }
          }
        }//#}}}

        function toggle_show_tracks(ul_id) { //#{{{
            console.log('showing tracks for ' + ul_id);
            var ul = document.getElementById(ul_id);
            console.log('ul.style.display: ' + ul.style.display);

            if (ul.style.display === "none") {
              console.log('setting display to block');
              ul.style.display = "block";
            } else {
              console.log('setting display to none');
              ul.style.display = "none";
            }
        }//#}}}

        function toggle_select_all(ul_id) { //#{{{
          var ul = document.getElementById(ul_id);
          console.log('toggling select all for ' + ul.id);
          // Iterate the checkbox elements in this ul, and toggle their state.
          var xs = ul.getElementsByClassName('track-select-button');
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
        }//#}}}

        // Start with lists hidden.
        toggle_lists();
        </script>
    </body>
    </html>
    '''#}}}

        return html#}}}

    elif request.method == 'POST':#{{{
        # request.form is a generator for a MultiDict object.
        #logging.warning(f'request.form: {list(request.form)}')
        #logging.warning(f'request.values: {list(request.values)}')
        # Each track is a string of: '<artist> <track>'.
        tracks = list(request.values)
        logging.warning(f'tracks={tracks!r}')

        # TODO: That's it! From here, I ought to be able to determine
        # the user's selections and go off and download them.

        # Use request.form.get method to prevent potentially raising werkzeug.exceptions.BadRequestKeyError:
        #form = request.form.get(name)#str
        #logging.warning(f'form: {form}')

        # TODO: I need static files for CSS & JS.

        if tracks:
            # TODO: If I start the downloads here, the page won't be rendered
            # till they're all finished.  I may have to run them in another
            # thread or something.
            logging.warning(f'there are tracks!')

            # TODO: get downloads_dir and mp3s_dir at runtime or programmatically.
            # this is a generator...
            # it performs the downloads, the extraction & conversion, and
            # then yields paths to the mp3s.
            download_mp3s(*tracks, downloads_dir='downloads', mp3s_dir='mp3s')

            return '''
            <html>
            <body>
            <p>Beginning downloads...</p>
            {}
            </body>
            </html>
            '''.format('<br>' + '\n'.join(f'{t!r}<br>' for t in tracks))

        else:
            logging.warning(f'tracks is None!!!')
            return '<html><body><p>tracks is None!!!</p></body></html>'

        #}}} end POST

#}}} end show_playlists



## This code gets executed after the webserver is started, but most likely
## before code within routes is executed.  And it could potentially hold up
## serving pages at the routes until it is processed.
#input('press return to continue ')
##
## This fucks shit up and makes a mess of the output!?
##
#logging.basicConfig(level='WARNING', style='{',
#        format='{level}:{lineno}:{funcName}:{message}:',)




if __name__ == '__main__':
    pass

    ### Using flask as web-server, instead of web-browser's file:// protocol.
    #os.environ['FLASK_APP'] = os.path.basename(__file__)
    ### `flask run` needs to be run in another thread!
    #try:
    #    os.system('flask run')
    #except OSError: # '[Errno 48] Address already in use'
    #    # Then what? Wait and loop a few times doing some retries?
    #    # Can I pass --port ?
    #    logging.warning('**** Caught OSError: [Errno 48] Address already in use...')
    #else:
    #    webbrowser.open('http://127.0.0.1:5000')



#=========================================================================={{{

#def get_track_attrs(track:dict) -> dict:#{{{
#    '''returns a dict of: artist, trackname, album, from a track dict.
#
#    where multiple artists are found for a track, only the first (primary)
#    is used.
#    '''
#    return {'artist': track['artists'][0]['name'],
#            'album': track['album']['name'],
#            'trackname': track['name'],
#            }
##}}} end get_track_attrs



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
