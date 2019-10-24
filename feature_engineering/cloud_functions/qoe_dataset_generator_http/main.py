"""
Cloud function to generate transcoded renditions and quality metrics from
video sources.
It is invoked from the bash script "call_cloud_function.sh" that iteratively
triggers an http call for each video entry located in the designated bucket
"""
import subprocess

from os import makedirs, path, remove
from os.path import exists, dirname

from google.cloud import storage
from google.api_core import retry

from urllib3.exceptions import ProtocolError

from imports import ffmpeg_installer

CODEC_TO_USE = 'libx264'

STORAGE_CLIENT = storage.Client()
PARAMETERS_BUCKET = 'livepeer-qoe-renditions-params'
SOURCES_BUCKET = 'livepeer-qoe-sources'
RENDITIONS_BUCKET = 'livepeer-qoe-renditions'


def check_blob(bucket_name, blob_name):
    """
    Checks if a file exists in the bucket.
    """

    bucket = STORAGE_CLIENT.get_bucket(bucket_name)
    stats = storage.Blob(bucket=bucket, name=blob_name).exists(STORAGE_CLIENT)

    print('File {} checked with status {}.'.format(blob_name, stats))
    return stats

def upload_blob(bucket_name, local_file, destination_blob_name):
    """
    Uploads a file to the bucket.
    """

    bucket = STORAGE_CLIENT.get_bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    print('Uploading {} to {}.'.format(
        local_file,
        destination_blob_name))

    blob.upload_from_filename(local_file)

    print('File {} uploaded to {}.'.format(
        local_file,
        destination_blob_name))

def download_to_local(bucket_name, local_file, origin_blob_name):
    """
    Downloads a file from the bucket.
    """

    predicate = retry.if_exception_type(ConnectionResetError, ProtocolError)
    reset_retry = retry.Retry(predicate)

    bucket = STORAGE_CLIENT.get_bucket(bucket_name)
    blob = bucket.blob(origin_blob_name)
    print(origin_blob_name)
    print('File download Started…. Wait for the job to complete.')
    # Create this folder locally if not exists
    local_folder = dirname(local_file)
    if not exists(local_folder):
        makedirs(local_folder)

    print('Downloading {} to {}'.format(origin_blob_name, local_file))
    reset_retry(blob.download_to_filename(local_file))
    print('Downloaded {} to {}'.format(origin_blob_name, local_file))

def trigger_renditions_bucket_event(data, context):
    """Background Cloud Function to be triggered by Cloud Storage.
       This function retrieves a source video and triggers
       the generation of renditions by means of an http asynchronous
       call to the create_renditions_http function

    Args:
        data (dict): The Cloud Functions event payload.
        context (google.cloud.functions.Context): Metadata of triggering event.
    Returns:
        None, the renditions cloud function are triggered asynchronously
    """

    name = data['name']

    resolutions = [1080, 720, 480, 384, 288, 144]
    qps = [45, 40, 32, 25, 21, 18, 14]

    for resolution in resolutions:
        for quantization_parameter in qps:
            local_file = '/tmp/{}-{}-{}.json'.format(name, resolution, quantization_parameter)
            remote_file = '{}/{}-{}.json'.format(name, resolution, quantization_parameter)
            file_output = open(local_file, "w")
            #file_output.write(json_file)
            file_output.close()
            upload_blob(PARAMETERS_BUCKET, local_file, remote_file)

    return 'Renditions triggered for {}'.format(name)

def create_renditions_bucket_event(data, context):
    """
    HTTP Cloud Function to generate video assets. Triggered by files
    deposited in PARAMETERS_BUCKET
    Args:
        data: The triggering object, containing name, resolution and quantization parameter
    Returns:
        The status message if successful
    """

    file_name = data['name']
    source_name = file_name.split('/')[0]
    resolution = file_name.split('/')[1].split('-')[0]
    qp_value = file_name.split('/')[1].split('-')[1].replace('.json', '')

    print('Processing source: {} at resolution {}'.format(source_name, resolution))

    # Locate the ffmpeg binary
    ffmpeg_installer.install()

    # Create the folder for the source asset
    source_folder = '/tmp/source'

    # Create the folder for the renditions
    renditions_folder = '/tmp/renditions'
    if not path.exists(renditions_folder):
        makedirs(renditions_folder)

    # Get the file that has been uploaded to GCS
    asset_path = {'path': '{}/{}'.format(source_folder, source_name)}

    # Check if the source is not already in the path
    if not path.exists(asset_path['path']):
        download_to_local(SOURCES_BUCKET, asset_path['path'], source_name)

    print('Processing resolution', resolution)
    # Create folder for each rendition

    bucket_path = '{}_{}/{}'.format(resolution, qp_value, source_name)
    if not check_blob(RENDITIONS_BUCKET, bucket_path):
        qp_path = '{}/{}_{}'.format(renditions_folder, resolution, qp_value)
        if not path.exists(qp_path):
            makedirs(qp_path)

    # Generate renditions with ffmpeg
    renditions_worker(asset_path['path'],
                      source_folder,
                      CODEC_TO_USE,
                      resolution,
                      qp_value,
                      renditions_folder)

    #compute_metrics(asset_path, renditions_paths)

    # Upload renditions to GCE storage bucket

    local_path = '{}/{}_{}/{}'.format(renditions_folder, resolution, qp_value, source_name)
    bucket_path = '{}_{}/{}'.format(resolution, qp_value, source_name)
    upload_blob(RENDITIONS_BUCKET, local_path, bucket_path)
    remove(local_path)

    return 'FINISHED Processing source: {} at resolution {}'.format(source_name, resolution)

def renditions_worker(full_input_file, source_folder, codec, resolution, qp_value, output_folder):
    """
    Executes ffmepg command via PIPE
    """

    #Formats ffmpeg command to be executed in parallel for each Quantization parameter value
    print('processing {}'.format(full_input_file))
    source_name = full_input_file.replace('{}/'.format(source_folder), '')

    ffmpeg_command = ['ffmpeg', '-y', '-i', '"{}"'.format(full_input_file),
                      '-c:v', codec,
                      '-vf',
                      'scale=-2:{}'.format(resolution),
                      '-qp {}'.format(qp_value),
                      '"{}/{}_{}/{}"'.format(output_folder, resolution, qp_value, source_name),
                      '-acodec copy'
                      ]

    ffmpeg = subprocess.Popen(' '.join(ffmpeg_command),
                              stderr=subprocess.PIPE,
                              stdout=subprocess.PIPE,
                              shell=True)
    out, err = ffmpeg.communicate()
    print(' '.join(ffmpeg_command), out, err)

def download_video_from_url(video_url, local_file, extension):
    """
    Downloads a video from a given url to an HLS manifest
    """
    local_folder = dirname(local_file)
    if not exists(local_folder):
        makedirs(local_folder)

    print('Downloading {} to {}'.format(video_url, local_file))
    ffmpeg_command = 'ffmpeg -y -i {} -vcodec copy -acodec copy -f {} {}'.format(video_url,
                                                                                 extension,
                                                                                 local_file)
    process = subprocess.Popen(ffmpeg_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()

    print(ffmpeg_command, output, error)
    if not exists(local_file):
        print('Unable to download {}'.format(local_file))
        return False

    return True

def create_source_http(request):
    """HTTP Cloud Function.
    Args:
        request (flask.Request): The request object.
        <http://flask.pocoo.org/docs/1.0/api/#flask.Request>
    Returns:
        The status message if successful
    """
    request_json = request.get_json(silent=True)
    request_args = request.args

    if request_json:
        playlist_url = request_json['playlist_url']
        video_id = request_json['video_id']
        extension = request_json['extension']

    elif request_args:
        playlist_url = request_args['playlist_url']
        video_id = request_args['video_id']
        extension = request_args['extension']
    else:
        return 'Unable to read request'
    print(playlist_url, video_id, extension)
    ffmpeg_installer.install()

    local_file = '/tmp/{}.{}'.format(video_id, extension)
    destination_blob_name = '{}.{}'.format(video_id, extension)

    if not check_blob(SOURCES_BUCKET, destination_blob_name):
        if download_video_from_url(playlist_url, local_file, extension):
            upload_blob(SOURCES_BUCKET, local_file, destination_blob_name)
    else:
        print('Video already uploaded, skipping')
    return 'FINISHED Processing source: {}'.format(video_id)