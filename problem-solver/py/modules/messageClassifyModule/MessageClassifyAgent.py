
import logging
from sc_client.models import ScAddr, ScTemplate
from sc_client.constants import sc_type
from sc_client.constants.common import ScEventType
from sc_client.client import search_by_template


from sc_kpm import ScAgentClassic, ScResult
from sc_kpm.sc_sets import ScSet, ScOrientedSet, ScStructure
from sc_kpm.utils import (
    get_link_content_data,
    get_element_system_identifier,
    generate_connector,
    generate_link,
    generate_node,
    generate_non_role_relation
)
from sc_kpm.utils.action_utils import (
    get_action_arguments,
    finish_action_with_status
)
from sc_kpm import ScKeynodes


from .classifier.MessageClassifier import MessageClassifier


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(name)s | %(message)s", datefmt="[%d-%b-%y %H:%M:%S]"
)


class MessageClassifyAgent(ScAgentClassic):
    def __init__(self):
        super().__init__("message_classify_action")
        self.classifier = MessageClassifier()


    def on_event(self, _1: ScAddr, _2: ScAddr, action_addr: ScAddr) -> ScResult:
        """Основной обработчик события классификации сообщения"""
        arc_to_message_addr = self._extract_action_argument(action_addr)
        message_link_addr = self._get_message_link(arc_to_message_addr)
        
        if not self._validate_message(message_link_addr, action_addr):
            return ScResult.SKIP
        
        message, message_author_class = self._get_message_data(message_link_addr)
        message_history = self._get_user_dialogue_messages(arc_to_message_addr)
        
        classification_result = self.classifier.classify(
            message, message_author_class, message_history
        )
        
        result_addr = self._build_classification_result(
            classification_result, message_author_class
        )
        
        generate_non_role_relation(action_addr, result_addr, ScKeynodes["nrel_result"])
        finish_action_with_status(action_addr, is_success=True)
        
        return ScResult.OK

    def _extract_action_argument(self, action_addr: ScAddr) -> ScAddr:
        """Извлекает первый аргумент действия"""
        [arc_to_message_addr] = get_action_arguments(action_addr, 1)
        return arc_to_message_addr

    def _validate_message(self, message_link_addr: ScAddr, action_addr: ScAddr) -> bool:
        """Валидирует сообщение перед обработкой"""
        if self._is_message_from_myself(message_link_addr):
            self.logger.debug("Message is from myself. Skip classification")
            finish_action_with_status(action_addr, is_success=False)
            return False
        
        if not self._get_message_author(message_link_addr).is_valid():
            self.logger.debug("Message author is not found")
            finish_action_with_status(action_addr, is_success=False)
            return False
        
        return True

    def _get_message_data(self, message_link_addr: ScAddr) -> tuple[str, str]:
        """Получает текст сообщения и класс автора"""
        message = get_link_content_data(message_link_addr)
        self.logger.info(f"MessageClassifyAgent: Message: {message}")
        
        message_author_class_addr = self._get_message_author_class(message_link_addr)
        message_author_class = get_element_system_identifier(message_author_class_addr)
        self.logger.info(f"MessageClassifyAgent: Message author class: {message_author_class}")
        
        return message, message_author_class

    def _build_classification_result(self, classification_result: tuple, 
                                   message_author_class: str) -> ScAddr:
        """Строит граф результатов классификации"""
        result_addr = generate_node(sc_type.CONST_NODE_STRUCTURE)
        
        message_topic_class, message_entities, message_context_entity_classes = classification_result
        
        self._add_topic_class_to_result(result_addr, message_topic_class)
        self._add_message_entities_to_result(result_addr, message_entities)
        self._add_context_entities_to_result(result_addr, message_context_entity_classes)
        
        return result_addr

    def _add_topic_class_to_result(self, result_addr: ScAddr, message_topic_class: str) -> None:
        """Добавляет класс темы сообщения в результат"""
        message_topic_class_addr = generate_link(message_topic_class)
        arc_addr = generate_connector(
            sc_type.CONST_PERM_POS_ARC, result_addr, message_topic_class_addr
        )
        generate_connector(
            sc_type.CONST_PERM_POS_ARC,
            ScKeynodes["rrel_message_topic_class_idtf"],
            arc_addr
        )
        self.logger.info(f"MessageClassifyAgent: Message topic class: {message_topic_class}")

    def _add_message_entities_to_result(self, result_addr: ScAddr, 
                                       message_entities: dict) -> None:
        """Добавляет сущности сообщения в результат"""
        entity_descriptions = ScOrientedSet()
        
        for entity_class, entity_value in message_entities.items():
            entity_description = self._create_entity_description(
                entity_value, entity_class
            )
            entity_descriptions.add(entity_description)
        
        arc_addr = generate_connector(
            sc_type.CONST_PERM_POS_ARC, result_addr, entity_descriptions.set_node
        )
        generate_connector(
            sc_type.CONST_PERM_POS_ARC,
            ScKeynodes["rrel_message_entity_descriptions"],
            arc_addr
        )
        
        self.logger.info(f"MessageClassifyAgent: Message entities: {message_entities}")

    def _create_entity_description(self, entity: str, entity_class: str) -> ScAddr:
        """Создаёт описание сущности"""
        entity_addr = generate_link(entity)
        entity_class_addr = generate_link(entity_class)
        entity_description = generate_node(sc_type.CONST_NODE)
        
        arc_addr = generate_connector(
            sc_type.CONST_PERM_POS_ARC, entity_description, entity_addr
        )
        generate_connector(
            sc_type.CONST_PERM_POS_ARC,
            ScKeynodes["rrel_message_entity_idtf"],
            arc_addr
        )
        
        arc_addr = generate_connector(
            sc_type.CONST_PERM_POS_ARC, entity_description, entity_class_addr
        )
        generate_connector(
            sc_type.CONST_PERM_POS_ARC,
            ScKeynodes["rrel_message_entity_class_idtf"],
            arc_addr
        )
        
        return entity_description

    def _add_context_entities_to_result(self, result_addr: ScAddr, 
                                       message_context_entity_classes: list) -> None:
        """Добавляет классы сущностей контекста сообщения в результат"""
        context_entity_class_descriptions = ScOrientedSet()
        
        for context_entity_class in message_context_entity_classes:
            context_entity_class_addr = generate_link(context_entity_class)
            context_entity_class_descriptions.add(context_entity_class_addr)
        
        arc_addr = generate_connector(
            sc_type.CONST_PERM_POS_ARC, result_addr, 
            context_entity_class_descriptions.set_node
        )
        generate_connector(
            sc_type.CONST_PERM_POS_ARC,
            ScKeynodes["rrel_message_context_entity_class_descriptions"],
            arc_addr
        )
        
        self.logger.info(f"MessageClassifyAgent: Context entities: {message_context_entity_classes}")

    def _get_message_link(self, arc_to_message_addr: ScAddr) -> ScAddr:
        """Получает файл с сообщением по дуге к нему"""
        templ = ScTemplate()
        templ.quintuple(
            sc_type.VAR_NODE,
            sc_type.VAR_POS_ARC,
            sc_type.VAR_NODE_LINK >> "message_link",
            arc_to_message_addr,
            ScKeynodes["rrel_last"]
        )
        return self._search_single_result(templ, "message_link")

    def _get_message_dialogue(self, arc_to_message_addr: ScAddr) -> ScAddr:
        """Получает диалог, к которому относится сообщение"""
        templ = ScTemplate()
        templ.triple(
            sc_type.VAR_NODE >> "message_dialogue",
            arc_to_message_addr,
            sc_type.VAR_NODE
        )
        return self._search_single_result(templ, "message_dialogue")

    def _get_message_author(self, message_link_addr: ScAddr) -> ScAddr:
        """Получает автора сообщения"""
        templ = ScTemplate()
        templ.quintuple(
            message_link_addr,
            sc_type.VAR_COMMON_ARC,
            sc_type.VAR_NODE >> "message_author",
            sc_type.VAR_POS_ARC,
            ScKeynodes["nrel_message_author"]
        )
        return self._search_single_result(templ, "message_author")

    def _get_message_author_class(self, message_link_addr: ScAddr) -> ScAddr:
        """Получает класс автора сообщения"""
        message_author_addr = self._get_message_author(message_link_addr)
        if not message_author_addr.is_valid():
            return ScAddr()
        
        templ = ScTemplate()
        templ.triple(
            sc_type.VAR_NODE_CLASS >> "message_author_class",
            sc_type.VAR_POS_ARC,
            message_author_addr
        )
        templ.triple(
            ScKeynodes["concept_user_class"],
            sc_type.VAR_POS_ARC,
            "message_author_class"
        )
        return self._search_single_result(templ, "message_author_class")

    def _search_single_result(self, template: ScTemplate, result_key: str) -> ScAddr:
        """Выполняет поиск и возвращает один результат"""
        results = search_by_template(template)
        if len(results) == 0:
            return ScAddr()
        return results[0].get(result_key)

    def _is_message_from_myself(self, message_link_addr: ScAddr) -> bool:
        """Проверяет, что сообщение от самого агента"""
        message_author_addr = self._get_message_author(message_link_addr)
        return message_author_addr == ScKeynodes["myself"]

    def _get_user_dialogue_messages(self, arc_to_message_addr: ScAddr) -> list[str]:
        """Получает историю сообщений в диалоге (исключая сообщения от самого агента)"""
        message_dialogue_addr = self._get_message_dialogue(arc_to_message_addr)
        if not message_dialogue_addr.is_valid():
            return []
        
        dialogue_messages = self._extract_dialogue_messages(message_dialogue_addr)
        dialogue_messages.reverse()
        return dialogue_messages

    def _extract_dialogue_messages(self, message_dialogue_addr: ScAddr) -> list[str]:
        """Извлекает все сообщения пользователя из диалога"""
        dialogue_messages = []
        dialogue_addr = ScOrientedSet(set_node=message_dialogue_addr)
        
        for message_link_addr in dialogue_addr:
            if self.is_message_from_myself(message_link_addr):
                message = get_link_content_data(message_link_addr)
                dialogue_messages.append(message)
        
        return dialogue_messages
