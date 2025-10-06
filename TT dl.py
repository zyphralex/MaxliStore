# name: TikTok Downloader
# version: 1.2.0
# developer: Kerdik
# id: tiktok_downloader
# dependencies: requests, aiofiles
# min-maxli: 29

import aiohttp
import aiofiles
import os
import re
import json
from urllib.parse import urlparse, urljoin

async def tiktok_command(api, message, args):
    """Скачивает видео из TikTok без водяных знаков."""
    if not args:
        await api.edit(message, "❌ Укажите ссылку на TikTok видео:\n.tiktok https://vm.tiktok.com/xxx/")
        return
    
    url = args[0]
    
    if not is_valid_tiktok_url(url):
        await api.edit(message, "❌ Неверная ссылка TikTok. Поддерживаются:\n• vm.tiktok.com\n• vt.tiktok.com\n• www.tiktok.com")
        return
    
    await api.edit(message, "⏳ Скачиваю видео...")
    
    try:
        video_info = await get_tiktok_video_enhanced(url)
        
        if not video_info or 'video_url' not in video_info:
            await api.edit(message, "❌ Не удалось получить видео. Попробуйте другую ссылку")
            return
        
        chat_id = await api.await_chat_id(message)
        
        temp_file = f"temp_tiktok_{message.id}.mp4"
        success = await download_video_file(video_info['video_url'], temp_file)
        
        if not success:
            await api.edit(message, "❌ Ошибка скачивания видео")
            return
        
        caption = f"📱 TikTok\n👤 Автор: {video_info.get('author', 'Неизвестно')}"
        
        if video_info.get('description'):
            desc = video_info['description'][:100] + "..." if len(video_info['description']) > 100 else video_info['description']
            caption += f"\n📝 {desc}"
        
        result = await api.send_file(
            chat_id=chat_id,
            file_path=temp_file,
            text=caption
        )
        
        try:
            os.remove(temp_file)
        except:
            pass
        
        if result:
            await api.delete(message)
        else:
            await api.edit(message, "❌ Ошибка отправки видео")
            
    except Exception as e:
        await api.edit(message, f"❌ Ошибка: {str(e)}")
        print(f"TikTok Downloader Error: {e}")

async def download_video_file(video_url, file_path):
    """Скачивает видео файл с обработкой ошибок."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(video_url) as response:
                if response.status == 200:
                    file_size = int(response.headers.get('content-length', 0))
                    
                    if file_size > 50 * 1024 * 1024:
                        return False
                    
                    async with aiofiles.open(file_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(1024*1024):
                            await f.write(chunk)
                    return True
                else:
                    print(f"HTTP Error: {response.status} for URL: {video_url}")
                    return False
    except Exception as e:
        print(f"Download error: {e}")
        return False

async def tiktok_info_command(api, message, args):
    """Показывает информацию о TikTok видео без скачивания."""
    if not args:
        await api.edit(message, "❌ Укажите ссылку на TikTok видео:\n.tiktok_info https://vm.tiktok.com/xxx/")
        return
    
    url = args[0]
    
    if not is_valid_tiktok_url(url):
        await api.edit(message, "❌ Неверная ссылка TikTok")
        return
    
    await api.edit(message, "⏳ Получаю информацию...")
    
    try:
        video_info = await get_tiktok_video_enhanced(url)
        
        if not video_info:
            await api.edit(message, "❌ Не удалось получить информацию о видео")
            return
        
        response_parts = [
            "📱 Информация о TikTok видео",
            f"👤 Автор: {video_info.get('author', 'Неизвестно')}",
            f"📝 Описание: {video_info.get('description', 'Нет описания')}"
        ]
        
        stats_added = False
        if video_info.get('likes'):
            response_parts.append(f"❤️ Лайки: {format_number(video_info['likes'])}")
            stats_added = True
        if video_info.get('comments'):
            response_parts.append(f"💬 Комментарии: {format_number(video_info['comments'])}")
            stats_added = True
        if video_info.get('shares'):
            response_parts.append(f"🔄 Репосты: {format_number(video_info['shares'])}")
            stats_added = True
        if video_info.get('views'):
            response_parts.append(f"👁️ Просмотры: {format_number(video_info['views'])}")
            stats_added = True
        
        if not stats_added:
            response_parts.append("📊 Статистика: Недоступна")
        
        if video_info.get('music'):
            response_parts.append(f"🎵 Музыка: {video_info['music']}")
        
        if video_info.get('duration'):
            response_parts.append(f"⏱️ Длительность: {video_info['duration']}сек")
        
        response_parts.append(f"\n💾 Для скачивания: `.tiktok {url}`")
        
        response_text = "\n".join(response_parts)
        await api.edit(message, response_text)
        
    except Exception as e:
        await api.edit(message, f"❌ Ошибка: {str(e)}")

def format_number(num):
    """Форматирует числа в красивый вид (1K, 1M и т.д.)"""
    if isinstance(num, (int, float)):
        if num >= 1000000:
            return f"{num/1000000:.1f}M"
        elif num >= 1000:
            return f"{num/1000:.1f}K"
        return str(num)
    return str(num)

async def get_tiktok_video_enhanced(url):
    """Пробует несколько API для получения максимальной информации."""
    apis_to_try = [
        get_tiktok_video_tikdown,
        get_tiktok_video_tikwm,
        get_tiktok_video_savetiktok,
    ]
    
    for api_func in apis_to_try:
        try:
            result = await api_func(url)
            if result and result.get('video_url'):
                print(f"Успешно использовано API: {api_func.__name__}")
                return result
        except Exception as e:
            print(f"Ошибка в {api_func.__name__}: {e}")
            continue
    
    return None

async def get_tiktok_video_tikdown(url):
    """Новое API - более надежное"""
    try:
        async with aiohttp.ClientSession() as session:
            api_url = "https://tikdown.org/api"
            
            payload = {
                "url": url
            }
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            
            async with session.post(api_url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('success'):
                        return {
                            'video_url': data.get('videoUrl', ''),
                            'author': data.get('author', 'Неизвестно'),
                            'description': data.get('description', 'Нет описания'),
                            'music': data.get('music', 'Н/Д')
                        }
        return None
    except Exception as e:
        print(f"Tikdown API error: {e}")
        return None

async def get_tiktok_video_tikwm(url):
    """TikWM API с исправлением ссылок"""
    try:
        async with aiohttp.ClientSession() as session:
            api_url = "https://www.tikwm.com/api/"
            
            payload = {
                "url": url,
                "count": 12,
                "cursor": 0,
                "web": 1,
                "hd": 1
            }
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
            }
            
            async with session.post(api_url, data=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('code') == 0:
                        video_data = data.get('data', {})
                        
                        video_url = video_data.get('play', '')
                        if video_url and not video_url.startswith('http'):
                            video_url = f"https://www.tikwm.com{video_url}"
                        
                        stats = video_data.get('stats', {})
                        
                        return {
                            'video_url': video_url,
                            'author': video_data.get('author', {}).get('nickname', 'Неизвестно'),
                            'description': video_data.get('title', 'Нет описания'),
                            'music': video_data.get('music_info', {}).get('title', 'Н/Д'),
                            'likes': stats.get('diggCount'),
                            'comments': stats.get('commentCount'),
                            'shares': stats.get('shareCount'),
                            'views': stats.get('playCount'),
                            'duration': video_data.get('duration')
                        }
        return None
    except Exception as e:
        print(f"TikWM API error: {e}")
        return None

async def get_tiktok_video_savetiktok(url):
    """SaveTikTok API - резервный вариант"""
    try:
        async with aiohttp.ClientSession() as session:
            api_url = "https://api.savetiktok.org/video"
            
            payload = {
                "url": url
            }
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Content-Type": "application/json",
            }
            
            async with session.post(api_url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('success'):
                        return {
                            'video_url': data.get('download_url', ''),
                            'author': data.get('author', {}).get('nickname', 'Неизвестно'),
                            'description': data.get('description', 'Нет описания'),
                        }
        return None
    except Exception as e:
        print(f"SaveTikTok API error: {e}")
        return None

def is_valid_tiktok_url(url):
    """Проверяет валидность ссылки TikTok."""
    tiktok_domains = [
        'vm.tiktok.com',
        'vt.tiktok.com', 
        'www.tiktok.com',
        'tiktok.com'
    ]
    
    try:
        parsed = urlparse(url)
        return any(domain in parsed.netloc for domain in tiktok_domains)
    except:
        return False

async def register(api):
    """Регистрирует команды модуля."""
    api.register_command("tiktok", tiktok_command)
    api.register_command("tiktok_info", tiktok_info_command)
