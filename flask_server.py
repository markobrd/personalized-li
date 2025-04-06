from flask import Flask, jsonify, send_from_directory, render_template, request
import datetime
import os
import json
import webbrowser
import yaml
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("linkedin_feed_server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load configuration
try:
    with open('config.yaml') as config_file:
        config = yaml.safe_load(config_file)
except Exception as e:
    logger.error(f"Failed to load config: {e}")
    config = {
        'posts_to_load': 5,
        'PORT': 5000
    }

# Constants
DATA_FOLDER = "JSON_DATA"
NUM_POSTS_PER_LOAD = config.get('posts_to_load', 5)
PORT = config.get('PORT', 5000)
TEMPLATE_FOLDER = "templates"

# Create folders if they don't exist
os.makedirs(DATA_FOLDER, exist_ok=True)
os.makedirs(TEMPLATE_FOLDER, exist_ok=True)

# Initialize Flask app
app = Flask(__name__, template_folder=TEMPLATE_FOLDER)

# Setup templates function - will be called during initialization
def setup_templates():
    try:
        # Path to the LinkedIn feed template
        template_path = os.path.join(TEMPLATE_FOLDER, 'linkedin_feed.html')
        
        # Check if the template already exists
        if not os.path.exists(template_path):
            # Template content (this would be your HTML template)
            with open('improved_linkedin_display.html', 'r') as f:
                template_content = f.read()
                
            # Save the template
            with open(template_path, 'w') as f:
                f.write(template_content)
                
            logger.info(f"LinkedIn feed template saved to {template_path}")
    except Exception as e:
        logger.error(f"Failed to setup templates: {e}")

# Call setup templates during initialization
setup_templates()

@app.route('/')
def home():
    """Render the LinkedIn feed page."""
    try:
        return render_template('linkedin_feed.html')
    except Exception as e:
        logger.error(f"Error rendering template: {e}")
        # Fallback to static HTML
        return send_from_directory('.', 'improved_linkedin_display.html')

@app.route('/api/placeholder/<width>/<height>')
def placeholder_image(width, height):
    """Generate a placeholder image URL."""
    return f"https://via.placeholder.com/{width}x{height}"

@app.route('/load_data', methods=['POST'])
def load_data():
    """
    Load posts data from JSON files.
    
    Request params:
    - file_index: Index of the file to start loading from
    - elem_index: Index of the element to start loading from
    
    Returns:
    - JSON with posts data and next indices
    """
    try:
        # Get request parameters
        file_index = int(request.json.get('file_index', 0))
        elem_index = int(request.json.get('elem_index', 0))
        
        # Get list of JSON files
        files = [f for f in sorted(os.listdir(DATA_FOLDER)) if f.endswith('.json')]
        
        if not files:
            logger.warning("No JSON files found in data folder")
            return jsonify({'data': [], 'next': -1, 'elem_index': -1})
        
        # Initialize variables
        posts_left_to_load = NUM_POSTS_PER_LOAD
        output_posts = []
        
        # Load posts from files
        while file_index < len(files) and file_index != -1 and posts_left_to_load > 0:
            file_path = os.path.join(DATA_FOLDER, files[file_index])
            
            # Skip non-JSON files
            if not file_path.endswith(".json"):
                file_index += 1
                continue
            
            # Load the JSON file
            try:
                with open(file_path) as f:
                    data = json.load(f)
            except Exception as e:
                logger.error(f"Error loading JSON file {file_path}: {e}")
                file_index += 1
                continue
            
            # Extract posts based on the element index and posts left to load
            if elem_index + posts_left_to_load <= len(data):
                # Take a slice of posts from current position
                output_posts.extend(data[elem_index:elem_index+posts_left_to_load])
                elem_index += posts_left_to_load
                posts_left_to_load = 0
            else:
                # Take all remaining posts from current file
                output_posts.extend(data[elem_index:])
                posts_taken = len(data) - elem_index
                posts_left_to_load -= posts_taken
                
                # Move to next file if available
                if file_index + 1 < len(files):
                    elem_index = 0
                    file_index += 1
                else:
                    file_index = -1  # No more files
        
        logger.info(f"Loaded {len(output_posts)} posts")
        return jsonify({
            'data': output_posts, 
            'next': file_index, 
            'elem_index': elem_index
        })
        
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return jsonify({'data': [], 'next': -1, 'elem_index': -1, 'error': str(e)})

@app.route('/feeds/<path:filename>')
def serve_feed(filename):
    """Serve saved feed HTML files."""
    return send_from_directory('saved_feeds', filename)

if __name__ == '__main__':
    # Open browser tab
    webbrowser.open_new_tab(f"http://127.0.0.1:{PORT}")
    
    # Start Flask server
    logger.info(f"Starting Flask server on port {PORT}")
    app.run(port=PORT, debug=False)