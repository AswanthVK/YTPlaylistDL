import os
import uuid
import time
import math
import asyncio
import logging
import threading
from youtube_dl import YoutubeDL
from youtube_dl.utils import (DownloadError, ContentTooShortError,
                ExtractorError, GeoRestrictedError,
                MaxDownloadsReached, PostProcessingError,
                UnavailableVideoError, XAttrMetadataError)
from asyncio import get_running_loop
from functools import partial
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
import pyrogram
from pyrogram import Client, filters
from pyrogram.errors import MessageNotModified
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant, UserBannedInChannel

import shutil

logging.basicConfig(
  level=logging.WARNING,
  format='%(name)s - [%(levelname)s] - %(message)s'
)
LOGGER = logging.getLogger(__name__)

# --- PROGRESS DEF --- #
async def progress_for_pyrogram(
  current,
  total,
  ud_type,
  message,
  start,
  filename
):
  now = time.time()
  diff = now - start
  if round(diff % 10.00) == 0 or current == total:
    percentage = current * 100 / total
    speed = current / diff
    elapsed_time = round(diff) * 1000
    time_to_completion = round((total - current) / speed) * 1000
    estimated_total_time = elapsed_time + time_to_completion
    elapsed_time = time_formatter(milliseconds=elapsed_time)
    estimated_total_time = time_formatter(milliseconds=estimated_total_time)
    progress = "○ **Name :** `{}`\n".format(filename)
    progress += "[{0}{1}] \n○ **Percentage :** `{2}%`\n○ **Completed :** ".format(
      ''.join(["█" for i in range(math.floor(percentage / 5))]),
      ''.join(["░" for i in range(20 - math.floor(percentage / 5))]),
      round(percentage, 1))

    tmp = progress + "`{0}` of `{1}`\n○ **Speed :** `{2}/s`\n○ **ETA :** `{3}`\n".format(
      humanbytes(current),
      humanbytes(total),
      humanbytes(speed),
      estimated_total_time if estimated_total_time != '' else "0 s",
    )
    try:
      await message.edit(
        text="{}\n {}".format(
          ud_type,
          tmp
        )
      )
    except MessageNotModified:
      pass

# --- HUMANBYTES DEF --- #
def humanbytes(size):
  if not size:
    return ""
  power = 2**10
  n = 0
  Dic_powerN = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
  while size > power:
    size /= power
    n += 1
  return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'

# --- TIME FORMATTER DEF --- #
def time_formatter(milliseconds: int) -> str:
  seconds, milliseconds = divmod(int(milliseconds), 1000)
  minutes, seconds = divmod(seconds, 60)
  hours, minutes = divmod(minutes, 60)
  days, hours = divmod(hours, 24)
  tmp = ((str(days) + "days, ") if days else "") + \
    ((str(hours) + " hours, ") if hours else "") + \
    ((str(minutes) + " minites, ") if minutes else "") + \
    ((str(seconds) + " seconds, ") if seconds else "") + \
    ((str(milliseconds) + " milliseconds, ") if milliseconds else "")
  return tmp[:-2]

# --- YTDL DOWNLOADER --- #
def ytdl_dowload(url, opts):
  try:
    with YoutubeDL(opts) as ytdl:
      ytdl.cache.remove()
      ytdl_data = ytdl.extract_info(url)
    filename = sorted(get_lst_of_files(out_folder, []))
    e = None
  except Exception as e:
    print(e)
    return filename, e

@Client.on_message(filters.regex(pattern=".*http.* (.*)"))
async def uloader(client, message):

  fsub = "@harp_tech"
  if not (await pyro_fsub(client, message, fsub) == True):
    return

  url = message.text.split(None, 1)[0]
  typee = message.text.split(None, 1)[1]
  #if not ("audio") or ("video") in message.text:
   # return await client.send_message(message.chat.id, "`Ooof.. Give file format. (audio/video)`")

  if "playlist?list=" in url:
    msg = await client.send_message(message.chat.id, '`Processing...`', reply_to_message_id=message.message_id)
  else:
    return await client.send_message(message.chat.id, '`I think this is invalid link...`', reply_to_message_id=message.message_id)

  out_folder = f"downloads/{uuid.uuid4()}/"
  if not os.path.isdir(out_folder):
    os.makedirs(out_folder)

  if (os.environ.get("USE_HEROKU") == "True") and (typee == "audio"):
    opts = {
      'format':'134',
      'addmetadata':True,
      'noplaylist': False,
      'writethumbnail':True,
      'geo_bypass':True,
      'nocheckcertificate':True,
      'outtmpl':out_folder + '%(title)s.%(ext)s',
      'quiet':False,
      'logtostderr':False
    }
    video = False
    song = True
  elif (os.environ.get("USE_HEROKU") == "False") and (typee == "audio"):
    opts = {
      'format':'134',
      'addmetadata':True,
      'noplaylist': False,
      'key':'FFmpegMetadata',
      'writethumbnail':True,
      'prefer_ffmpeg':True,
      'geo_bypass':True,
      'nocheckcertificate':True,
      'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '320',
      }],
      'outtmpl':out_folder + '%(title)s.%(ext)s',
      'quiet':False,
      'logtostderr':False
    }
    video = False
    song = True

  if (os.environ.get("USE_HEROKU") == "False") and (typee == "video"):
    opts = {
      'format':'135',
      'addmetadata':True,
      'noplaylist': False,
      'xattrs':True,
      'writethumbnail': True,
      'key':'FFmpegMetadata',
      'prefer_ffmpeg':True,
      'geo_bypass':True,
      'nocheckcertificate':True,
      'postprocessors': [{
        'key': 'FFmpegVideoConvertor',
        'preferedformat': 'mp4'},],
      'outtmpl':out_folder + '%(title)s.%(ext)s',
      'logtostderr':False,
      'quiet':False
    }
    song = False
    video = True
  elif (os.environ.get("USE_HEROKU") == "True") and (typee == "video"):
    opts = {
      'format':'135',
      'addmetadata':True,
      'noplaylist': False,
      'xattrs':True,
      'writethumbnail': True,
      'geo_bypass':True,
      'nocheckcertificate':True,
      'videoformat':'mp4',
      'outtmpl':out_folder + '%(title)s.%(ext)s',
      'logtostderr':False,
      'quiet':False
    }
    song = False
    video = True

  try:
    await msg.edit("`Downloading Playlist...`")
    loop = get_running_loop()
    filename, e = await loop.run_in_executor(None, partial(ytdl_dowload, url, opts))
    if not e == None:
      return await msg.edit(str(e))
  except:
    pass
    
  c_time = time.time()
  try:
    await msg.edit("`Downloaded.`")
  except MessageNotModified:
    pass
  if song:
    for single_file in filename:
      if os.path.exists(single_file):
        if single_file.endswith((".mp4", ".mp3", ".flac", ".webm")):
          try:
            ytdl_data_name_audio = os.path.basename(single_file)
            tnow = time.time()
            fduration, fwidth, fheight = get_metadata(single_file)
            await message.reply_chat_action("upload_audio")
            await client.send_audio(
              message.chat.id,
              single_file,
              caption=f"**File:** `{ytdl_data_name_audio}`",
              duration=fduration,
              progress=progress_for_pyrogram,
              progress_args=("🎗 **__Uploading...__**", msg, tnow, ytdl_data_name_audio)
            )
          except Exception as e:
            await msg.edit("{} caused `{}`".format(single_file, str(e)))
            continue
          await message.reply_chat_action("cancel")
          os.remove(single_file)
    LOGGER.info(f"Clearing {out_folder}")
    shutil.rmtree(out_folder)
    await del_old_msg_send_msg(msg, client, message)

  if video:
    for single_file in filename:
      if os.path.exists(single_file):
        if single_file.endswith((".mp4", ".mp3", ".flac", ".webm")):
          try:
            ytdl_data_name_video = os.path.basename(single_file)
            tnow = time.time()
            fduration, fwidth, fheight = get_metadata(single_file)
            await message.reply_chat_action("upload_video")
            await client.send_video(
              message.chat.id,
              single_file,
              caption=f"**File:** `{ytdl_data_name_video}`",
              supports_streaming=True,
              duration=fduration,
              width=fwidth,
              height=fheight,
              progress=progress_for_pyrogram,
              progress_args=("🎗 **__Uploading...__**", msg, tnow, ytdl_data_name_video)
            )
          except Exception as e:
            await msg.edit("{} caused `{}`".format(single_file, str(e)))
            continue
          await message.reply_chat_action("cancel")
          os.remove(single_file)
    LOGGER.info(f"Clearing {out_folder}")
    shutil.rmtree(out_folder)
    await del_old_msg_send_msg(msg, client, message)
    

def get_lst_of_files(input_directory, output_lst):
  filesinfolder = os.listdir(input_directory)
  for file_name in filesinfolder:
    current_file_name = os.path.join(input_directory, file_name)
    if os.path.isdir(current_file_name):
      return get_lst_of_files(current_file_name, output_lst)
    output_lst.append(current_file_name)
  return output_lst

async def del_old_msg_send_msg(msg, client, message):
  await msg.delete()
  await client.send_message(message.chat.id, "`Playlist Upload Success!`")

def get_metadata(file):
  fwidth = None
  fheight = None
  fduration = None
  metadata = extractMetadata(createParser(file))
  if metadata is not None:
    if metadata.has("duration"):
      fduration = metadata.get('duration').seconds
    if metadata.has("width"):
      fwidth = metadata.get("width")
    if metadata.has("height"):
      fheight = metadata.get("height")
  return fduration, fwidth, fheight

async def pyro_fsub(c, message, fsub):
  try:
    user = await c.get_chat_member(fsub, message.chat.id)
    if user.status == "kicked":
      await c.send_message(
        chat_id=message.chat.id,
        text="Sorry, You are Banned to use me. Contact my [Support Group](https://t.me/harp_chat).",
        parse_mode="markdown",
        disable_web_page_preview=True
      )
    return True
  except UserNotParticipant:
    await c.send_message(
      chat_id=message.chat.id,
      text="**Please Join My Updates Channel to Use Me!**",
      reply_markup=InlineKeyboardMarkup(
        [
          [
            InlineKeyboardButton("Join Now", url="https://t.me/harp_tech")
          ]
        ]
      )
    )
    return False
  except Exception as kk:
    print(kk)
    await c.send_message(
      chat_id=message.chat.id,
      text="Something went Wrong. Contact my [Support Group](https://t.me/harp_chat).",
      parse_mode="markdown",
      disable_web_page_preview=True)
    return False

print("> Bot Started ")
