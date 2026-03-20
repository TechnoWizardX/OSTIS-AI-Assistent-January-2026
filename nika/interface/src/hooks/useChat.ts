import { useCallback, useEffect, useRef, useState } from 'react';
import { ScAddr, ScEventSubscriptionParams, ScEventType, ScType, ScTemplate } from 'ts-sc-client';
import { client } from '@api';
import { findDialogueByUser } from '@api/sc/agents/dialogAgent';
import { getInfoMessage, searchChatMessages } from '@api/sc/search/searchChatMessages';
import { generateNewMessage } from '@api/sc/agents/generateNewMessage';

interface IMessage {
    addr: ScAddr;
    text: string | number;
    id: number;
    time: string | number;
    date: string;
    author: ScAddr;
    isLoading?: boolean;
}

export const useChat = (userAddr: ScAddr | null) => {
    const [messages, setMessages] = useState<IMessage[]>([]);
    const [chatAddr, setChatNode] = useState<ScAddr | null>(null);
    const [shouldEnd, setShouldEnd] = useState(false);
    const [isAgentAnswer, setIsAgentAnswer] = useState(false);

    const chatRef = useRef<HTMLDivElement>(null);

    const subscribeToMessage = useCallback(async () => {
        if (!chatAddr) return;

        const myself = "myself";
        const nrelReplyToMessage = "nrel_reply_to_message";
        const nrelMessageAuthor = 'nrel_message_author';

        const baseKeynodes = [
            { id: myself, type: ScType.ConstNode },
            { id: nrelReplyToMessage, type: ScType.ConstNodeNonRole },
            { id: nrelMessageAuthor, type: ScType.ConstNodeNonRole },
        ];

        const keynodes = await client.resolveKeynodes(baseKeynodes);

        const onMessageReplied = async (_subscribedAddr: ScAddr, _arc: ScAddr, messageToReplyMessageArcAddr: ScAddr) => {
            const replyMessageAlias = '_reply_message';

            const template = new ScTemplate();
            template.triple(
                [ScType.VarNodeLink, replyMessageAlias],
                messageToReplyMessageArcAddr,
                ScType.VarNodeLink,
            );
            const result = await client.searchByTemplate(template);
            if (!result.length) return;
            const replyMessageAddr = result[0].get(replyMessageAlias);

            const replyMessage = await getInfoMessage(replyMessageAddr, keynodes);

            if (!replyMessage || !userAddr) return;

            setMessages((prev) => {
                return [...prev.filter((el) => el.id !== replyMessage.id), replyMessage];
            });
            setIsAgentAnswer(false);
        };
        const eventParams = new ScEventSubscriptionParams(keynodes[nrelReplyToMessage], ScEventType.AfterGenerateOutgoingArc, onMessageReplied);
        await client.createElementaryEventSubscriptions([eventParams]);
    }, [chatAddr, userAddr]);

    const minNumberMessages = () => {
        const MIN_MESSAGE_HEIGHT = 60;

        if (!chatRef.current) return 0;
        const height = chatRef.current.scrollHeight;
        return Math.ceil((height / MIN_MESSAGE_HEIGHT) * 1.2);
    };

    const initChat = useCallback(async (userAddr: ScAddr) => {
        let chatAddr = await findDialogueByUser(userAddr);
        if (!chatAddr) return;

        const { messages, shouldEnd } = await searchChatMessages(chatAddr, minNumberMessages());
        console.log(messages);
        if (!messages) return;
        setShouldEnd(shouldEnd);
        setMessages(messages);
        setChatNode(chatAddr);
    }, []);

    useEffect(() => {
        subscribeToMessage();
    }, [subscribeToMessage]);

    const onFetching = useCallback(async () => {
        const lastMessageAddr = messages[0].addr;
        if (shouldEnd || !chatAddr) return;

        const { messages: newMessages, shouldEnd: localShouldEnd } = await searchChatMessages(
            chatAddr,
            minNumberMessages(),
            lastMessageAddr,
        );
        setMessages((prev) => [...newMessages, ...prev]);

        return localShouldEnd;
    }, [chatAddr, shouldEnd, messages]);

    const sendMessage = useCallback(
        async (userAddr: ScAddr, text: string) => {
            const messageAddr = await generateNewMessage(text, userAddr);
            const chatAddr = await findDialogueByUser(userAddr);
            if (!chatAddr) return;
            setChatNode(chatAddr);
            if (!messageAddr || !chatAddr) return;
            const date = new Date();
            const message = {
                id: messageAddr.value,
                text,
                author: userAddr,
                time: `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`,
                date: `${date.getFullYear()}.${(date.getMonth() + 1).toString().padStart(2, '0')}.${date
                    .getDate()
                    .toString()
                    .padStart(2, '0')}`,
                addr: chatAddr,
                isLoading: false,
            };
            setMessages((prev) => [...prev, message]);

            setIsAgentAnswer(true);
        },
        [chatAddr],
    );

    return { initChat, sendMessage, isAgentAnswer, onFetching, messages, chatRef };
};
