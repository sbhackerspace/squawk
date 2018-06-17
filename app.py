#!/usr/bin/python3

# Copyright 2018 Garrett Holmstrom
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3 of the License or (at your
# option) any later version accepted by the Santa Barbara Hackerspace (or
# its successor approved by the Santa Barbara Hackerspace), which shall
# act as a proxy as defined in Section 14 of version 3 of the license.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see http://www.gnu.org/licenses/.

"""\
SQUAWK - Parrot-powered Text-to-Speech

Available requests:
    GET  /{stage}
        Display general information about the service.

    GET  /{stage}/voices
        Return a JSON document describing available voices.

    POST /{stage}/wav
        Convert the supplied text to speech in WAV format.

        Headers:

               Accept:  must be set to audio/wav

            x-api-key:  must be set to your API key

        Query string parameters:

                 rate:  audio sampling rate in Hz (8000 or 16000, default 8000)

                voice:  name of the voice to use
"""

import contextlib
import tempfile
import wave

import boto3
import chalice


DEFAULT_SAMPLE_RATE = 8000
DEFAULT_VOICE = 'Matthew'
MAX_TEXT_BYTES = 20480


app = chalice.Chalice(app_name='squawk')
app.debug = False
POLLY = boto3.client('polly')


@app.route('/')
def show_help():
    app.log.debug('show_help')
    return chalice.Response(
        body=__doc__.format(stage=app.current_request.context['stage']),
        headers={'Content-Type': 'text/plain'},
        status_code=200)


@app.route('/voices')
def get_voices():
    voices = POLLY.describe_voices().get('Voices') or []
    app.log.debug('get_voices')
    return {'voices': sorted(voices, key=lambda x: x['Name'])}


@app.route('/wav', methods=['POST'], api_key_required=True,
           content_types=['application/json',
                          'application/x-www-form-urlencoded'])
def synthesize_wav():
    params = app.current_request.query_params or {}
    sample_rate = int(params.get('rate', str(DEFAULT_SAMPLE_RATE)))
    voice = params.get('voice', DEFAULT_VOICE)
    app.log.debug('synthesize_wav({}, {}, <{} bytes>)'.format(
        sample_rate, voice, len(app.current_request.raw_body)))
    response = POLLY.synthesize_speech(
        OutputFormat='pcm', SampleRate=str(sample_rate),
        Text=app.current_request.raw_body.decode('utf-8'), VoiceId=voice)
    with contextlib.closing(response['AudioStream']) as stream:
        with tempfile.TemporaryFile() as temp:
            output = wave.open(temp, 'wb')
            output.setnchannels(1)
            output.setsampwidth(2)  # 16 bits per sample
            output.setframerate(sample_rate)
            output.writeframes(stream.read())
            output.close()
            temp.seek(0)
            return chalice.Response(
                body=temp.read(),
                headers={'Content-Type': 'audio/wav'},
                status_code=200)
