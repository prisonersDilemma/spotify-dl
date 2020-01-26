#!/usr/bin/env python3
__doc__ = """
"""
__date__ = '2020-01-25'
__version__ = (0,0,1)
#__all__ = ('',)

import glob
import logging
import os
import re
import shlex
import subprocess
import sys
from youtube_dl import YoutubeDL
from youtube_search import YoutubeSearch


def get_youtube_top_result(search_terms):#{{{
    # results is actually a list of dicts, with keys: 'title', 'link', 'id'.
    #logging.warning(f'search_terms={search_terms!r}')

    results = YoutubeSearch(search_terms, max_results=10).to_dict()
    # for now, choose the first result only.  In the future, can add
    # interaction for user choice.
    return 'https://www.youtube.com' + results[0]['link']#}}}



# TODO: Is there an easier way with less I/O to do this,
# rather than having to create 3 files and delete 2 of them?
def extract_audio(vidpath, mp3s_dir) -> str:#{{{
    '''extract the audio stream from vidpath and up-convert it to 320 kb/s mp3.
    delete both the video and default audio files.
    return the path to the mp3.
    '''
    def get_audio_codec(video_path:str):#{{{
        ''' return the name of the audio codec given a <video_path>.  '''
        command_line = shlex.split(f'ffprobe -hide_banner -loglevel info "{video_path}"')
        proc = subprocess.Popen(command_line, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc.wait()
        output = proc.stderr.read().decode()
        try:
            ## the Audio stream's pattern in `ffprobe` output.
            #audio_stream = re.compile(r'\bAudio:\s(?P<codec>\w+)')
            #return audio_stream.search(output).group('codec')
            return re.search(r'\bAudio:\s(?P<codec>\w+)', output).group('codec')
        except AttributeError:
            #sys.stderr.write(f'---- ffprobe output ----\n{output}\n')
            #raise ValueError(f'Audio stream not found for: {video_path!r}')
            logging.error(f'failed to get audio codec from: {video_path!r}')
        #}}} end get_audio_codec

    def convert_to_mp3(audpath, mp3_dst) -> int:#{{{
        '''up-convert the audio file to 320K bp/s
        and remove the original.
        '''
        '''convert <audio_src> to a 320k mp3 file at <mp3_dst>
        returns the exit code of ffmpeg.
        '''
        command_line = shlex.split(f'ffmpeg -hide_banner -loglevel info -i "{audpath}" -b:a 320000 "{mp3_dst}"')
        proc = subprocess.Popen(command_line,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,)
        proc.wait()
        return proc.returncode
    #}}} end convert_to_mp3

    # mapping of audio codecs/formats to extensions.
    audio_codec_exts = {
        'aac': 'aac',
        'opus': 'opus',
        'vorbis': 'ogg',
        }
    audio_codec = get_audio_codec(vidpath)
    audio_ext = audio_codec_exts[audio_codec]
    logging.warning(f'audio_codec={audio_codec!r}, audio_ext={audio_ext!r}')

    vidbase = os.path.splitext(vidpath)[0]
    audio_dst = '.'.join((vidbase, audio_ext))
    name = os.path.splitext(os.path.basename(vidpath))[0]
    mp3_dst = os.path.join(mp3s_dir, '.'.join((name, 'mp3')))
    logging.warning(f'vidbase={vidbase!r}, '
                    f'audio_dst={audio_dst!r}, '
                    f'name={name!r}, '
                    f'mp3_dst={mp3_dst!r}')

    command_line = shlex.split(f'ffmpeg -hide_banner -loglevel info -i "{vidpath}" -vn -acodec copy "{audio_dst}"')
    proc = subprocess.Popen(command_line,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,)
    proc.wait()

    if convert_to_mp3(audio_dst, mp3_dst) is 0:
        logging.warning('successfully extracted audio to 320 kb/s '
                        f'mp3_dst={mp3_dst!r}; removing video={vidpath!r} '
                        f'and default audio stream={audio_dst!r}')
        os.remove(vidpath)
        os.remove(audio_dst)
        logging.warning(f'removed vidpath: {vidpath!r}')
        logging.warning(f'removed audio_dst: {audio_dst!r}')
        return mp3_dst

    #}}} end extract_audio


# DEBUG
#def download_mp3s(*tracks, downloads_dir, mp3s_dir):
#    logging.warning(f'downloads_mp3s called!')
def download_mp3s(*tracks, downloads_dir='./downloads', mp3s_dir='./mp3s'):#{{{
    '''Download tracks from YouTube, extract the audio streams and up-convert
    them to mp3s @ 320kb/s. Remove the original files (video and audio) only
    keeping the mp3. Generates a list of each mp3 as the process is completed.

    <downloads_dir> path to where youtube-dl videos will be downloaded to;
                    default is "downloads".
    <mp3s_dir>      path to where mp3s will be saved; default is "mp3s".

    --ignore-config
    --config-location PATH
    --output=PATH
    --extract-audio
    --audio-format=mp3
    --audio-quality=320K
    #return os.system('youtube-dl {}'.format(' '.join(vidurls)))
    '''
    #logging.warning(f'downloads_mp3s called!')
    #logging.warning(f'tracks={tracks!r}')

    # what directory to download to?
    # This one (as per Flask, as it is using this as the web-root,
    # essentially...I think)
    downloads_dir = os.path.realpath(downloads_dir)
    logging.warning(f'downloads_dir={downloads_dir!r}')
    if not os.path.isdir(downloads_dir):
        os.mkdir(downloads_dir)
        logging.warning(f'created downloads_dir: {downloads_dir!r}')

    # TODO: create the mp3s directory if it doesn't exist; this should
    # be done somewhere else, where the mp3s dir will be specified.
    mp3s_dir = os.path.realpath(mp3s_dir)
    if not os.path.isdir(mp3s_dir):
        logging.warning(f'creating mp3s directory at: {mp3s_dir!r}')
        os.mkdir(mp3s_dir)


    for track in tracks:
        #logging.warning(f'searching for track: {track!r}')

        url = get_youtube_top_result(track)
        logging.warning(f'youtube top result: url={url!r}')

        # NOTE: this is how/where the downloads_dir is specified; like --output
        # in the config when run at the command-line.
        params = {'outtmpl': os.path.join(downloads_dir, '%(id)s.%(ext)s'), }
        logging.warning(f'params={params!r}')
        ydl = YoutubeDL(params=params)
        # YoutubeDL.download needs to be passed a list or tuple of urls!
        urls = (url,)
        with ydl:
            ydl.download(urls)

        # get the path of the downloaded file.
        videoid = os.path.basename(url).split('watch?v=')[-1]
        logging.warning(f'videoid={videoid!r}')
        vidpath = os.path.join(downloads_dir, videoid)
        logging.warning(f'vidpath={vidpath!r}')
        #logging.warning(f'videoid={videoid!r}, vidpath={vidpath!r}')

        try:
            vidpath = glob.glob(f'{vidpath}*')[0]
            logging.warning(f'vidpath={vidpath!r}')
        except IndexError:
            logging.error(f'could not find file for: track={track!r}, url={url!r}')
            return

        else:
            logging.warning(f'extracting mp3 from: {vidpath!r}')
            # TODO: finally, move the mp3s to a directory.
            mp3_dst = extract_audio(vidpath, mp3s_dir)
            logging.warning(f'mp3 -> {mp3_dst!r}')

            # TODO: I should use shlex or something to better handle quoting.
            os.system('mv "{mp3_dst}" "{mp3s_dir}"')

            logging.warning(f'moved to mp3s_dir: {mp3_dst!r} -> {mp3s_dir!r}')

            # TODO: As a generator, this will break the route rendering for Flask.
            #yield os.path.join(mp3s_dir, mp3_dst)

    #}}} end download






if __name__ == '__main__':
    pass

#=========================================================================={{{
#==========================================================================}}}
