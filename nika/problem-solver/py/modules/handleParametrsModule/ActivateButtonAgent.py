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

class ActivateButtonAgent(ScAgentClassic):
    def __init__(self):
        super().__init__("action_act_button")


    def on_event(self, _1: ScAddr, _2: ScAddr, action_addr: ScAddr) -> ScResult:
        [button] = get_action_arguments(action_addr, 1)

        button = self._get_param_main_idtf(button)
        self.logger.info(f'Button: {button}')



        if button == "вайфай":
            subprocess.Popen(["nmcli", "radio", "wifi", "on"])

        elif button == "блютуз":
            subprocess.Popen(["rfkill", "unblock", "bluetooth"])

        elif button == "авиарежим":
            subprocess.run(["nmcli", "radio", "wifi", "off"], check=True)
            subprocess.run(["nmcli", "radio", "wwan", "off"], check=True)
            subprocess.run(["rfkill", "block", "bluetooth"], check=True)

        elif button == "энергосбережение":
            subprocess.Popen(["powerprofilesctl", "set", "power-saver"])

        elif button == '':
            self._set_unk_button_message(action_addr)

        else:
            self._set_unk_button_message(action_addr)

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

    def _set_unk_button_message(self, action_addr: ScAddr) -> None:
        """Создание сообщения об ошибке"""
        error_message_link = generate_link('Данной кнопки не существует в базе знаний или её нет на вашем компьютере')
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

