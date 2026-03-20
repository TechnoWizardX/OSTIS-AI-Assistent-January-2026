import { ScType} from 'ts-sc-client';
import { client } from '@api/sc';

const Ivanov = 'Ivanov';

const baseKeynodes = [
    { id: Ivanov, type: ScType.ConstNode },
];

export const getUser = async () => {
    const keynodes = await client.resolveKeynodes(baseKeynodes);
    return keynodes[Ivanov];
};
