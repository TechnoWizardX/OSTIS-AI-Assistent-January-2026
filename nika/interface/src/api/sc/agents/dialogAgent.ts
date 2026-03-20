import { ScAddr, ScTemplate, ScType } from 'ts-sc-client';
import { client } from '@api/sc/client';

const conceptDialogue = 'concept_dialogue';
const nrelDialogueParticipants = 'nrel_dialogue_participants';
const myself = 'myself';

const baseKeynodes = [
    { id: conceptDialogue, type: ScType.ConstNodeClass },
    { id: nrelDialogueParticipants, type: ScType.ConstNodeNonRole },
    { id: myself, type: ScType.ConstNode },
];

export const findDialogueByUser = async (userAddr: ScAddr) => {
    const keynodes = await client.resolveKeynodes(baseKeynodes);

    const dialogue = '_dialogue';
    const participants = '_participants';
    const template = new ScTemplate();
    template.triple(
        keynodes[conceptDialogue],
        ScType.VarPosArc,
        [ScType.VarNode, dialogue],
    );
    template.quintuple(
        dialogue,
        ScType.VarCommonArc,
        [ScType.VarNode, participants],
        ScType.VarPosArc,
        keynodes[nrelDialogueParticipants],
    );
    template.triple(
        participants,
        ScType.VarPosArc,
        userAddr
    );
    const result = await client.searchByTemplate(template);

    if (result.length) {
        return result[0].get(dialogue);
    }

    return null;
};
