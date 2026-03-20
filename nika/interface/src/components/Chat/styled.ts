import styled from 'styled-components';

const sharedStyle = `
    font-family: 'Roboto';
    font-style: normal;
    font-weight: 400;
    font-size: 16px;
    line-height: 10px;
    background: #ffffffff;
    border: 2px solid rgba(100, 150, 150, 0.2);
    box-shadow: 2px 2px 4px rgba(131, 129, 129, 0.18);
    color: #222;
    transition: box-shadow 0.2s, background 0.25s;
`;

export const WrapperGlobalSpinner = styled.div`
    height: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
`;

export const Wrapper = styled.div`
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    background: white;
    box-sizing: border-box;
    box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.25);
    backdrop-filter: blur(10px);
    border-radius: 15px;
`;
export const SearchBar = styled.div`
    display: flex;
    justify-content: flex-end;
    background: rgba(99, 132, 102, 0.43);
`;
export const Main = styled.div`
    height: 100%;
    position: relative;
    padding-top: 16px;
    display: flex;
    flex-direction: column;
    overflow: auto;
    color: rgba(0, 0, 0, 0);
    transition: color 0.3s ease;
    &::-webkit-scrollbar,
    &::-webkit-scrollbar-thumb {
        width: 12px;
        border-radius: 13px;
        background-clip: padding-box;
        border: 4px solid transparent;
    }
    &::-webkit-scrollbar-thumb {
        box-shadow: inset 0 0 0 10px;
    }
    &:hover {
        color: rgba(122, 142, 137, 1);
    }
`;
export const WrapperSpinner = styled.div`
    width: 142px;
    height: 31px;
    margin: auto;
    display: flex;
    padding: 8px 12px;
    margin-bottom: 12px;
    background: #daeddc;
    border-radius: 3px;
`;
export const FetchingSpinnerText = styled.div`
    margin-left: 6px;
    font-family: 'Roboto';
    font-style: normal;
    font-weight: 400;
    font-size: 12px;
    line-height: 14px;
    color: #707070;
`;

export const AnswerSpinnerText = styled.div`
    margin-left: 8px;
    font-family: 'Robot';
    font-style: normal;
    font-weight: 400;
    font-size: 14px;
    line-height: 18px;
    color: #949494;
`;
export const ArrowWrapper = styled.div`
    position: absolute;
    bottom: 80px;
    right: 13px;
    width: 50px;
    height: 50px;
    display: flex;
    justify-content: center;
    align-items: center;
    border-radius: 50%;
    background: #f9f3f0;
    z-index: 5;
    cursor: pointer;
    &:hover {
        background: #e4e0dd;
    }
`;
export const WrapperIcon = styled.div`
    width: 22px;
    height: 25px;
`;
export const WrapperAgentAnswer = styled.div`
    height: 25px;
    display: flex;
`;
export const WrapperWaitingSpinner = styled.div`
    display: flex;
    align-items: center;
`;
export const WrapperFooter = styled.div`
    display: flex;
`;
export const Footer = styled.div`
    margin-left: 9px;
    margin-right: 12px;
    padding-bottom: 9px;
`;
export const FooterInput = styled.input`
    ${sharedStyle}
    padding: 13px 18px;
    border-radius: 35px;
    outline: none;
    flex: 1 1 auto;
    margin-right: 12px;
    background: #f9f3f0;
`;
export const FooterSend = styled.button`
    ${sharedStyle}
    padding: 0;
    width: 54px;
    height: 54px;
    border-radius: 50%;
    display: flex;
    justify-content: center;
    align-items: center;
    cursor: pointer;
    margin-left: 0;
    background: #faf6f2ff;
    &:hover {
        background: #e6e1dd;
        box-shadow: 0 0 8px #b5c0ba77;
    }
    &:active {
        background: #dcc3a0;
        box-shadow: 0 0 8px #aaa;
    }
`;
export const WrapperSendIcon = styled.div`
    width: 33px;
    height: 27px;
`;
