import { ScAddr, ScTemplate, ScType } from 'ts-sc-client';
import { client } from "@api";

const rrel1 = 'rrel_1';
const nrelMessageAuthor = 'nrel_message_author';
const nrelBasicSequence = 'nrel_basic_sequence';
const rrelLast = 'rrel_last';

const baseKeynodes = [
    { id: rrel1, type: ScType.ConstNodeRole },
    { id: nrelMessageAuthor, type: ScType.ConstNodeNonRole },
    { id: nrelBasicSequence, type: ScType.ConstNodeNonRole },
    { id: rrelLast, type: ScType.ConstNodeRole },
];

interface IMessage {
    addr: ScAddr;
    text: string | number;
    id: number;
    time: string | number;
    date: string;
    author: ScAddr;
}

const findLastMessage = async (chatAddr: ScAddr, keynodes: Record<string, ScAddr>) => {
    const messagesAlias = '_message';
    const template = new ScTemplate();

    template.quintuple(
        chatAddr,
        ScType.VarPosArc,
        [ScType.VarNode, messagesAlias],
        ScType.VarPosArc,
        keynodes[rrelLast],
    );
    const resultMessages = await client.searchByTemplate(template);
    if (resultMessages.length) {
        return resultMessages[0].get(messagesAlias);
    }
    return null;
};

const findCurrentArc = async (chatAddr: ScAddr, messageAddr: ScAddr) => {
    const currentArcAlias = '_current_arc';

    const template = new ScTemplate();
    template.triple(chatAddr, [ScType.VarPosArc, currentArcAlias], messageAddr);
    const resultLastMessageEdge = await client.searchByTemplate(template);

    if (resultLastMessageEdge.length) {
        return resultLastMessageEdge[0].get(currentArcAlias);
    }
    return null;
};

const findPreviousMessage = async (chatAddr: ScAddr, previousArc: ScAddr) => {
    const previousMessageAlias = '_previous_message';

    const template = new ScTemplate();
    template.triple(chatAddr, previousArc, [ScType.VarNode, previousMessageAlias]);

    const result = await client.searchByTemplate(template);
    if (result.length) {
        return result[0].get(previousMessageAlias);
    }
    return null;
};

const findPreviousArc = async (chatAddr: ScAddr, keynodes: Record<string, ScAddr>, currentMessageArc: ScAddr) => {
    const previousMessageArcAlias = '_previous_message_arc';

    const template = new ScTemplate();

    template.quintuple(
        [ScType.VarPosArc, previousMessageArcAlias],
        ScType.VarCommonArc,
        currentMessageArc,
        ScType.VarPosArc,
        keynodes[nrelBasicSequence],
    );

    const result = await client.searchByTemplate(template);
    if (result.length) {
        return result[0].get(previousMessageArcAlias);
    }
    return null;
};

export const getInfoMessage = async (messageAddr: ScAddr, keynodes: Record<string, ScAddr>) => {
    const authorAlias = '_author_node';

    const template = new ScTemplate();

    template.quintuple(
        messageAddr,
        ScType.VarCommonArc,
        [ScType.VarNode, authorAlias],
        ScType.VarPosArc,
        keynodes[nrelMessageAuthor],
    );
    const result = await client.searchByTemplate(template);

    if (!result.length) return;

    const author = result[0].get(authorAlias);

    const resultText = await client.getLinkContents([messageAddr]);
    const text = resultText[0].data;

    const date = new Date();

    return {
        id: messageAddr.value,
        text,
        time: `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`,
        date: `${date.getFullYear()}.${(date.getMonth() + 1).toString().padStart(2, '0')}.${date
            .getDate()
            .toString()
            .padStart(2, '0')}`,
        author: author,
        addr: messageAddr
    };
};

const checkRrel1 = async (keynodes: Record<string, ScAddr>, chatNode: ScAddr, messageNode: ScAddr) => {
    const template = new ScTemplate();
    template.quintuple(
        chatNode,
        ScType.VarPosArc,
        messageNode,
        ScType.VarPosArc,
        keynodes[rrel1],
    );
    const result = await client.searchByTemplate(template);

    return !!result.length;
};

const getFirstMessages = async (
    chatNode: ScAddr,
    keynodes: Record<string, ScAddr>,
    amount: number,
    lastMessageAddr?: ScAddr,
) => {
    const messages: IMessage[] = [];
    const defaultReturn = { messages: [], shouldEnd: false };
    let count = 0;
    let currentMessage = lastMessageAddr || (await findLastMessage(chatNode, keynodes));

    if (!currentMessage) return defaultReturn;

    let currentArc = await findCurrentArc(chatNode, currentMessage);

    if (!currentArc) return defaultReturn;

    const lastMessage = await getInfoMessage(currentMessage, keynodes);
    if (!lastMessage) return defaultReturn;
    if (!lastMessageAddr) messages.push(lastMessage);

    while (count < amount) {
        count++;
        if (!currentMessage) break;
        currentArc = await findPreviousArc(chatNode, keynodes, currentArc);

        if (!currentArc) break;

        currentMessage = await findPreviousMessage(chatNode, currentArc);

        if (!currentMessage) break;

        const message = await getInfoMessage(currentMessage, keynodes);
        if (!message) break;
        messages.unshift(message);
    }
    const shouldEnd = messages[0] ? await checkRrel1(keynodes, chatNode, messages[0].addr) : true;

    return { messages, shouldEnd };
};

export const searchChatMessages = async (chatNode: ScAddr, amount: number, lastMessageAddr?: ScAddr) => {
    const keynodes = await client.resolveKeynodes(baseKeynodes);
    return await getFirstMessages(chatNode, keynodes, amount, lastMessageAddr);
};
