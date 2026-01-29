import json
from datetime import datetime
from sc_kpm import ScKeynodes
from sc_client.client import (connect, disconnect, is_connected,
                              generate_elements, generate_by_template,
                              search_links_by_contents, search_by_template, 
                              create_elementary_event_subscriptions, get_link_content)
from sc_client.constants import sc_type 
from sc_client.models import (ScAddr, ScLinkContent, ScConstruction, 
                            ScLinkContentType, ScTemplate,
                            ScEventSubscriptionParams)
from sc_client.constants.common import ScEventType
from SystemControl import SystemControler


class DataExchanger():
    # функции работы с историей чата
    @staticmethod
    def update_chat_history(text, author, day, time):
        message = {
            "author" : author,
            "text" : text,
            "time" : time,
            "day" : day
        }
        with open("chat_history.json", "r", encoding="utf-8") as file:
            history = json.load(file)

        history.append(message)
        
        with open("chat_history.json", "w", encoding="utf-8") as file:
            json.dump(history, file, ensure_ascii=False, indent=4)
    
    @staticmethod
    def clear_chat_history():
        with open("chat_history.json", "w", encoding="utf-8") as file:
            json.dump([], file, ensure_ascii=False, indent=4)

    @staticmethod
    def get_chat_history():
        with open("chat_history.json", "r", encoding="utf-8") as file:
            history = json.load(file)
        return history
    

    # функции работы с конфигурацией
    @staticmethod
    def modify_config(data_key, new_data):
        with open("config.json", "r", encoding="utf-8") as file:
            config = json.load(file)

        config[data_key] = new_data
        with open("config.json", "w", encoding="utf-8") as file:
            json.dump(config, file, ensure_ascii=False, indent = 4)
    
    @staticmethod
    def get_config():
        with open("config.json", "r", encoding="utf-8") as file:
            config = json.load(file)
        return config
    
    @staticmethod
    def get_themes():
        with open("themes.json", "r", encoding="utf-8") as file:
            return json.load(file)
    
    @staticmethod
    def save_themes(new_user_theme_config):
        with open("themes.json", "r", encoding="utf-8") as file:
            new_theme_config = json.load(file)
        new_theme_config["user"] = new_user_theme_config

        with open("themes.json", "w", encoding="utf-8") as file:
            json.dump(new_theme_config, file, ensure_ascii=False, indent=4)
    
    @staticmethod
    def save_name_exe_pair(name, exe):
        with open("name_exe_pair.json", "r", encoding="utf-8") as file:
            list = json.load(file)
        list[name] = exe
        with open("name_exe_pair.json", "w", encoding="utf-8") as file:
            json.dump(list, file, ensure_ascii=False, indent=4)

    @staticmethod
    def get_name_exe_pair():
        with open("name_exe_pair.json", "r", encoding="utf-8") as file:
            return json.load(file)

    # функции исполнительной системы
    @staticmethod
    def return_message_to_user(message):
        return message["message_to_user"]
    
    @staticmethod
    def start_system_instuctions(message):
        SystemControler.classify_action(message)

    # функции работы с NIKA
    @staticmethod
    def send_to_nika(text: str):
        nrelMessageAuthor = "nrel_message_author"
        userAddr = ScKeynodes["Ivanov"]    
        keynodes = ScKeynodes[nrelMessageAuthor]
        message = "_message"

        construction = ScConstruction()
        construction.generate_link(sc_type.CONST_NODE_LINK, ScLinkContent(text, ScLinkContentType.STRING), message)
        message_addr = generate_elements(construction)
        
        template = ScTemplate()
        template.quintuple(
            message_addr[0],
            sc_type.VAR_COMMON_ARC,
            userAddr,
            sc_type.VAR_PERM_POS_ARC,
            keynodes
        )
        result = generate_by_template(template)
    
    @staticmethod
    def resolve_user_agent():
        return ScKeynodes["Ivanov"]
    
    @staticmethod
    def subscribe_to_message(message_adder) -> list:
        myself = "myself"
        nrel_reply_to_message = "nrel_reply_to_message"
        nrel_message_author = "nrel_message_author"

        keynode_myself = ScKeynodes[myself]
        keynode_nrel_reply_to_message = ScKeynodes[nrel_reply_to_message]
        keynode_nrel_message_author = ScKeynodes[nrel_message_author]

        def on_message_replied(subscribed_addr: ScAddr, arc: ScAddr,
                               message_to_reply_message_arc_addr: ScAddr):
            reply_message_alias = "_reply_message"

            template = ScTemplate()
            template.triple(
                sc_type.VAR_NODE_LINK >> reply_message_alias,
                message_to_reply_message_arc_addr,
                sc_type.VAR_NODE_LINK
            )
            result = search_by_template(template)
            if not result:
                return 
            reply_message_addr = result[0].get(reply_message_alias)
            text = get_link_content(reply_message_addr)[0].data

            DataExchanger.update_chat_history(text, "nika", datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%H:%M"))
            author = "nika"
            date = datetime.now().strftime("%Y-%m-%d")
            current_time = datetime.now().strftime("%H:%M")
            message_adder(author, text, date, current_time)

        event_params = ScEventSubscriptionParams(keynode_nrel_reply_to_message, 
                                                    ScEventType.AFTER_GENERATE_OUTGOING_ARC, on_message_replied)
        return create_elementary_event_subscriptions(event_params)



class ScConnection():
    
    _connected = False

    @staticmethod
    def connect_to_sc_server():
        if not is_connected():
            connect("ws://127.0.0.1:8090")
            ScConnection._connected = True

    @staticmethod
    def disconnect_from_sc_server():
        if is_connected():
            disconnect()
            ScConnection._connected = False

    @staticmethod
    def is_connected():
        return ScConnection._connected


    