import re
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
#test:yes

class IncreaseParametrAgent(ScAgentClassic):
    def __init__(self):
        super().__init__("action_increase_parametr")


    def on_event(self, _1: ScAddr, _2: ScAddr, action_addr: ScAddr) -> ScResult:
        [param_node, value_link, units_link] = get_action_arguments(action_addr, 3)

        parametr = self._get_param_main_idtf(param_node)
        self.logger.info(f'Parametr: {parametr}')
        value = int(get_link_content_data(value_link))
        self.logger.info(f'Value: {value}')
        units = int(get_link_content_data(units_link))
        self.logger.info(f'Units: {units}')

        
        
        if parametr == "звук":

            result = subprocess.run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"],capture_output=True,text=True,check=True)

            volume_line = result.stdout.splitlines()[0]
            volume_percent = int(volume_line.split('/')[1].strip().replace('%', ''))

            value = volume_percent
            self.logger.info('Change volume')

            if value + units <= 100:
                subprocess.run(
                    ["/usr/bin/pactl", "set-sink-volume", "@DEFAULT_SINK@", f"+{units}%"],check=True
                )
            else:
                self.logger.info('Invalid operation')
                self._set_max_message(action_addr)
                subprocess.run(["/usr/bin/pactl", "set-sink-volume", "@DEFAULT_SINK@", "100%"],check=True)#ставим максимальное значение
                finish_action_with_status(action_addr, is_success=False)
                return ScResult.NO
           
            value += units

        elif parametr == "яркость":
            self.logger.info('Change brightness')

            result = subprocess.run(["brightnessctl", "get"],capture_output=True,text=True,check=True)#для получения текущего значения яркости на устройстве
            current_brightness = int(result.stdout.strip())
            result_max = subprocess.run(["brightnessctl", "max"],capture_output=True,text=True,check=True)
            max_brightness = int(result_max.stdout.strip())
            brightness_percent = int(current_brightness / max_brightness * 100)

            value = brightness_percent 
            
            if value + units <= 100:
                self.logger.info(f'Current brightness', value)
                subprocess.run(
                    ["brightnessctl", "set", f"+{units}%"], check=True
                )
                value += units
            else:
                self.logger.info('Invalid operation')
                self._set_max_message(action_addr)
                subprocess.run(["brightnessctl", "set", "100%"],check=True)##ставим максимальное значение
                finish_action_with_status(action_addr, is_success=False)
                return ScResult.NO
       
        
        set_link_contents(ScLinkContent(data=str(value), addr=value_link, content_type=ScLinkContentType.STRING))
        self.logger.info(f'New value: {value}')

        finish_action_with_status(action_addr, is_success=True)
        return ScResult.OK
    
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

    def _set_max_message(self, action_addr: ScAddr) -> None:
        """Создание сообщения об ошибке"""
        error_message_link = generate_link('Так как ваше значение слишком велико, будет установлено максимальное значение параметра')#задаётся сообщение ошибки
        templ = ScTemplate()
        templ.quintuple(
            action_addr,
            sc_type.VAR_COMMON_ARC,
            error_message_link,
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes['nrel_max_message']
        )
        templ.triple(
            ScKeynodes['concept_message'],
            sc_type.VAR_PERM_POS_ARC,
            error_message_link
        )
        generate_by_template(templ)

