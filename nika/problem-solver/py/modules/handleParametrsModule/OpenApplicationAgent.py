import webbrowser
import subprocess
import logging
from sc_client.models import ScAddr, ScLinkContent, ScLinkContentType, ScTemplate
from sc_client.client import set_link_contents, search_by_template, generate_by_template
from sc_client.constants import sc_type


from sc_kpm import ScAgentClassic, ScResult
from sc_kpm.utils import (
    get_link_content_data,
    generate_link
)
from sc_kpm.utils.action_utils import (
    get_action_arguments,
    finish_action_with_status
)
from sc_kpm import ScKeynodes

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(name)s | %(message)s", datefmt="[%d-%b-%y %H:%M:%S]"
)
# добавить разные браузеры

class OpenApplicationAgent(ScAgentClassic):
    def __init__(self):
        super().__init__("action_open_app")


    def on_event(self, _1: ScAddr, _2: ScAddr, action_addr: ScAddr) -> ScResult:
        [application] = get_action_arguments(action_addr, 1)

        application = self._get_param_main_idtf(application)
        self.logger.info(f'Application: {application}')

        if application == "браузер":
            webbrowser.open_new_tab("https://www.google.com")

        elif application == "настройки":
            subprocess.Popen(["gnome-control-center"])

        elif application == "проводник":
            subprocess.Popen(["nautilus"])
        else:
            self._set_unk_app_message(action_addr)

    def _get_param_main_idtf(self, param_node: ScAddr) -> str:
        """Получает основной идентификатор параметра"""
        templ = ScTemplate()
        templ.quintuple(
            param_node,
            sc_type.VAR_COMMON_ARC,
            sc_type.VAR_NODE_LINK >> '_idtf',
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes['nrel_main_idtf']
        )
        main_idtf_link = self._search_single_result(templ, '_idtf')
        return get_link_content_data(main_idtf_link)

    def _search_single_result(self, template: ScTemplate, result_key: str) -> ScAddr:
        """Выполняет поиск и возвращает один результат"""
        results = search_by_template(template)
        if len(results) == 0:
            return ScAddr()
        return results[0].get(result_key)

    def _set_unk_app_message(self, action_addr: ScAddr) -> None:
        """Создание сообщения об ошибке"""
        error_message_link = generate_link('Данного приложения не существует в базе знаний')
        templ = ScTemplate()
        templ.quintuple(
            action_addr,
            sc_type.VAR_COMMON_ARC,
            error_message_link,
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes['nrel_error_message']
        )
        templ.triple(
            ScKeynodes['concept_message'],
            sc_type.VAR_PERM_POS_ARC,
            error_message_link
        )
        generate_by_template(templ)

