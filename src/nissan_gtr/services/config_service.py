import yaml
from pathlib import Path
from datetime import datetime
import base64
import uuid

def get_config():
    config_path = Path(__file__).parent.parent / 'config.yaml'
    if not config_path.exists():
        return {'Term': 'fall', 'Users': []}
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    if config is None:
        config = {}
    if 'Users' not in config:
        config['Users'] = []
    return config

def save_config(config):
    config_path = Path(__file__).parent.parent / 'config.yaml'
    with open(config_path, 'w') as file:
        yaml.dump(config, file)

def get_term():
    return get_config().get('Term', 'fall')

def get_users():
    return get_config().get('Users', [])

def get_user_by_uuid(user_uuid):
    users = get_users()
    for user in users:
        if user_uuid in user:
            return user[user_uuid]
    return None

def get_user_courses(user_uuid):
    user = get_user_by_uuid(user_uuid)
    return user.get('courses', []) if user else []

def get_user_ntfy_topic(user_uuid):
    user = get_user_by_uuid(user_uuid)
    return user.get('ntfy_topic') if user else None

def get_user_logfile(user_uuid):
    user = get_user_by_uuid(user_uuid)
    return user.get('logfile') if user else None

def add_user(name):
    config = get_config()
    user_uuid = str(uuid.uuid4())
    ntfy_topic = f"gt_registration_{base64.b64encode(name.encode()).decode().rstrip('=')}"
    new_user = {
        user_uuid: {
            'name': name,
            'ntfy_topic': ntfy_topic,
            'logfile': f"{name.lower()}_log.txt",
            'courses': []
        }
    }
    if 'Users' not in config:
        config['Users'] = []
    config['Users'].append(new_user)
    save_config(config)
    return user_uuid, new_user[user_uuid]


def add_crn_to_user(user_uuid, crn):
    config = get_config()
    for user in config['Users']:
        if user_uuid in user:
            if crn not in user[user_uuid]['courses']:
                user[user_uuid]['courses'].append(crn)
                save_config(config)
                return True
    return False

def convert_term_to_code(term):
    now = datetime.now()
    year = now.year

    if term.lower() == 'spring':
        year += 1 if now.month > 4 else year
        return f'{year}02'
    elif term.lower() == 'summer':
        return f'{year}05'
    elif term.lower() == 'fall':
        return f'{year}08'
    else:
        raise ValueError("Invalid term. Use 'spring', 'summer', or 'fall'.")

def get_user_uuid_by_name(name):
    users = get_users()
    for user in users:
        for uuid, user_data in user.items():
            if user_data['name'] == name:
                return uuid
    return None
