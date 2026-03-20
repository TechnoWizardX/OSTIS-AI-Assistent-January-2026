import { useCallback, useEffect, useState, Fragment } from 'react';
import { Wrapper, ChatWrapper, SCgViewerWrapper } from "./styled";
import { Message } from '@components/Chat/Message';
import { Chat } from '@components/Chat';
import { Date } from '@components/Chat/Date';
import { ScAddr } from 'ts-sc-client';
import { getUser } from '@agents/resolveUserAgent';
import { useChat } from '@hooks/useChat';
import { SC_WEB_URL } from "@constants";

export const Demo = () => {
    const [userAddr, setUser] = useState<ScAddr | null>(null);
    const [isLoading, setIsLoading] = useState(false);

    const { initChat, sendMessage, isAgentAnswer, onFetching, messages, chatRef } = useChat(userAddr);
    const onSend = useCallback(
        async (text: string) => {
            if (!userAddr) return;
            await sendMessage(userAddr, text);
        },
        [userAddr, sendMessage],
    );

    const url = SC_WEB_URL + '/?sys_id=answer_structure&scg_structure_view_only=true';

    useEffect(() => {
        (async () => {
            setIsLoading(true);
            const userAddr = await getUser();
            if (!userAddr) return;
            setUser(userAddr);
            await initChat(userAddr);
            setIsLoading(false);
        })();
    }, []);

    return (
        <Wrapper>
            <ChatWrapper>
                <Chat
                    ref={chatRef}
                    isLoading={isLoading}
                    onSend={onSend}
                    onFetching={onFetching}
                    isAgentAnswer={isAgentAnswer}
                >
                    {messages.map((item, ind) => {
                        const prevItem = messages[ind - 1];
                        const showDate = item.date !== prevItem?.date;
                        return (
                            <Fragment key={item.id}>
                                {showDate && <Date date={item.date} />}
                                <Message
                                    isLeft={!!userAddr && !item.author.equal(userAddr)}
                                    time={item.time}
                                    isLoading={item.isLoading}
                                >
                                    {typeof item.text === 'string' ? (
                                        <div style={{whiteSpace: "pre-wrap"}} dangerouslySetInnerHTML={{__html: item.text/*.replace(/\n/g, '<br />').replace(/\t/g, '&nbsp;&nbsp;').replace(/  /g, '&nbsp;&nbsp;')*/}} />

                                    ) : (
                                    <div>{item.text}</div>
                                    )}

                                </Message>
                            </Fragment>
                        );
                    })}
                </Chat>
            </ChatWrapper>
            <SCgViewerWrapper>
                <iframe src={url} style={{width: '100%', height: '100%', border: 0, borderRadius: '15px'}}/>
            </SCgViewerWrapper>
        </Wrapper>
    );
};
