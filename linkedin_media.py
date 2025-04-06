"""
Media Support for LinkedIn Scraper
----------------------------------
This module adds media content detection and extraction to the LinkedIn scraper.
It should be integrated with the main scraper module to enhance LinkedIn posts with media content.
"""

import logging
import re
from typing import Dict, List, Optional, Union
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class LinkedInMediaExtractor:
    """Class to handle media extraction from LinkedIn posts."""
    
    @staticmethod
    def extract_media_from_post(post_div: BeautifulSoup, post_data: Dict) -> Dict:
        """
        Extract media content from a LinkedIn post.
        
        Args:
            post_div: BeautifulSoup element containing the post
            post_data: Existing post data dictionary
            
        Returns:
            Updated post data dictionary with media content
        """
        try:
            # Check for image content
            image_container = post_div.find('div', class_='update-components-image')
            if image_container:
                LinkedInMediaExtractor._extract_image_content(image_container, post_data)
                
            # Check for multiple images
            images_container = post_div.find('div', class_='update-components-carousel')
            if images_container:
                LinkedInMediaExtractor._extract_carousel_content(images_container, post_data)
                
            # Check for video content
            video_container = post_div.find('div', class_='update-components-video')
            if video_container:
                LinkedInMediaExtractor._extract_video_content(video_container, post_data)
                
            # Check for document content
            document_container = post_div.find('div', class_='update-components-document')
            if document_container:
                LinkedInMediaExtractor._extract_document_content(document_container, post_data)
                
            # Check for poll content
            poll_container = post_div.find('div', class_='update-components-poll')
            if poll_container:
                LinkedInMediaExtractor._extract_poll_content(poll_container, post_data)
                
            # Extract URLs from the post text that might be media
            LinkedInMediaExtractor._extract_media_from_text(post_data)
                
            return post_data
            
        except Exception as e:
            logger.error(f"Error extracting media content: {e}")
            return post_data
    
    @staticmethod
    def _extract_image_content(image_container: BeautifulSoup, post_data: Dict) -> None:
        """Extract image content from a LinkedIn post."""
        try:
            image_element = image_container.find('img')
            if not image_element:
                return
                
            image_url = image_element.get('src')
            if not image_url:
                return
                
            # Check for a caption
            caption_element = image_container.find('div', class_='feed-shared-image__description')
            caption = caption_element.get_text(strip=True) if caption_element else None
            
            post_data['media_content'] = {
                'type': 'image',
                'url': image_url,
                'alt': image_element.get('alt', 'LinkedIn image'),
                'caption': caption
            }
            
        except Exception as e:
            logger.error(f"Error extracting image content: {e}")
    
    @staticmethod
    def _extract_carousel_content(carousel_container: BeautifulSoup, post_data: Dict) -> None:
        """Extract multiple images from a carousel in a LinkedIn post."""
        try:
            image_elements = carousel_container.find_all('img')
            if not image_elements:
                return
                
            image_urls = []
            for img in image_elements:
                img_src = img.get('src')
                if img_src:
                    image_urls.append(img_src)
            
            if image_urls:
                post_data['media_content'] = image_urls
                
        except Exception as e:
            logger.error(f"Error extracting carousel content: {e}")
    
    @staticmethod
    def _extract_video_content(video_container: BeautifulSoup, post_data: Dict) -> None:
        """Extract video content from a LinkedIn post."""
        try:
            # Try to get video thumbnail
            thumbnail_element = video_container.find('img')
            thumbnail_url = thumbnail_element.get('src') if thumbnail_element else None
            
            # Try to get video URL
            video_element = video_container.find('video')
            video_url = video_element.get('src') if video_element else None
            
            if not (thumbnail_url or video_url):
                return
                
            # Check for a caption
            caption_element = video_container.find('div', class_='feed-shared-video__description')
            caption = caption_element.get_text(strip=True) if caption_element else None
            
            post_data['media_content'] = {
                'type': 'video',
                'url': video_url,
                'thumbnail': thumbnail_url,
                'caption': caption
            }
            
        except Exception as e:
            logger.error(f"Error extracting video content: {e}")
    
    @staticmethod
    def _extract_document_content(document_container: BeautifulSoup, post_data: Dict) -> None:
        """Extract document content from a LinkedIn post."""
        try:
            # Try to get document title
            title_element = document_container.find('div', class_='feed-shared-document__title')
            title = title_element.get_text(strip=True) if title_element else "Document"
            
            # Try to get thumbnail
            thumbnail_element = document_container.find('img')
            thumbnail_url = thumbnail_element.get('src') if thumbnail_element else None
            
            post_data['media_content'] = {
                'type': 'document',
                'title': title,
                'thumbnail': thumbnail_url
            }
            
        except Exception as e:
            logger.error(f"Error extracting document content: {e}")
    
    @staticmethod
    def _extract_poll_content(poll_container: BeautifulSoup, post_data: Dict) -> None:
        """Extract poll content from a LinkedIn post."""
        try:
            options = []
            
            option_elements = poll_container.find_all('div', class_='feed-shared-poll-option')
            for option_elem in option_elements:
                text_elem = option_elem.find('span', class_='feed-shared-poll-option__text')
                text = text_elem.get_text(strip=True) if text_elem else "Option"
                
                # Try to get percentage
                percent_elem = option_elem.find('span', class_='feed-shared-poll-option__percentage')
                percent_text = percent_elem.get_text(strip=True) if percent_elem else "0%"
                percent = int(percent_text.strip('%') or 0)
                
                options.append({
                    'text': text,
                    'percent': percent
                })
            
            # Try to get votes count
            votes_elem = poll_container.find('div', class_='feed-shared-poll__info')
            votes_text = votes_elem.get_text(strip=True) if votes_elem else ""
            votes_match = re.search(r'(\d+)\s+votes?', votes_text)
            votes = int(votes_match.group(1)) if votes_match else 0
            
            # Try to get time left
            time_left_match = re.search(r'(\d+\s+\w+\s+left)', votes_text)
            time_left = time_left_match.group(1) if time_left_match else "Poll closed"
            
            post_data['media_content'] = {
                'type': 'poll',
                'options': options,
                'votes': votes,
                'timeLeft': time_left
            }
            
        except Exception as e:
            logger.error(f"Error extracting poll content: {e}")
    
    @staticmethod
    def _extract_media_from_text(post_data: Dict) -> None:
        """Extract media links from post text."""
        if 'post_text' not in post_data or not post_data['post_text']:
            return
            
        text = post_data['post_text']
        
        # Check for image links in the post text
        image_urls = []
        
        # Look for image URLs with common extensions
        image_pattern = r'https?://[^\s]+\.(?:jpg|jpeg|png|gif|webp)(?:\?[^\s]*)?'
        image_matches = re.findall(image_pattern, text)
        
        if image_matches:
            for url in image_matches:
                image_urls.append(url)
        
        # If we found image URLs and no media content is set yet, add them
        if image_urls and 'media_content' not in post_data:
            if len(image_urls) == 1:
                post_data['media_content'] = {
                    'type': 'image',
                    'url': image_urls[0]
                }
            else:
                post_data['media_content'] = image_urls
        
        # Check for YouTube links
        youtube_pattern = r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)'
        youtube_match = re.search(youtube_pattern, text)
        
        if youtube_match and 'media_content' not in post_data:
            video_id = youtube_match.group(1)
            post_data['media_content'] = {
                'type': 'video',
                'url': f'https://www.youtube.com/embed/{video_id}',
                'thumbnail': f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg'
            }


# Function to integrate with the existing scraper
def enhance_post_with_media_content(post_div: BeautifulSoup, post_data: Dict) -> Dict:
    """
    Wrapper function to enhance a post with media content.
    This can be called from the main LinkedIn scraper.
    
    Args:
        post_div: BeautifulSoup element containing the post
        post_data: The post data dictionary
        
    Returns:
        Updated post data dictionary with media content
    """
    return LinkedInMediaExtractor.extract_media_from_post(post_div, post_data)