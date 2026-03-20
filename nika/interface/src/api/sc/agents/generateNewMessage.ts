import {ScConstruction, ScLinkContent, ScLinkContentType, ScTemplate, ScType, ScAddr} from 'ts-sc-client';
import { client } from '@api/sc';

const nrelMessageAuthor = 'nrel_message_author';

const baseKeynodes = [
    { id: nrelMessageAuthor, type: ScType.ConstNodeNonRole },
];

export const generateNewMessage = async (text: string, userAddr: ScAddr) => {
    const keynodes = await client.resolveKeynodes(baseKeynodes);
    const message = '_message';

    let construction = new ScConstruction();
    construction.generateLink(ScType.ConstNodeLink, new ScLinkContent(text, ScLinkContentType.String), message);
    const [messageAddr] = await client.generateElements(construction);

    const template = new ScTemplate();
    template.quintuple(
        messageAddr,
        ScType.VarCommonArc,
        userAddr,
        ScType.VarPermPosArc,
        keynodes[nrelMessageAuthor]
    );
    const result = await client.generateByTemplate(template);
    return messageAddr;
};
