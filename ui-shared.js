/**
 * University Activity Calendar - Shared UI Utilities
 * Standardized components for Toast, Loading, and Global Interactions
 */

// 1. Toast Notification System
window.toast = function(msg, type = 'success') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = `
            position: fixed; bottom: 20px; right: 20px; z-index: 9999;
            display: flex; flex-direction: column; gap: 10px; pointer-events: none;
        `;
        document.body.appendChild(container);
    }

    const div = document.createElement('div');
    div.style.cssText = `
        padding: 14px 22px; border-radius: 12px; background: white; color: #1e293b;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        display: flex; align-items: center; gap: 12px; font-size: 14px; font-weight: 600;
        border-left: 5px solid #10b981; min-width: 300px; transform: translateX(130%);
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        pointer-events: auto;
    `;

    // Dark mode support
    if (document.documentElement.classList.contains('dark-theme')) {
        div.style.background = '#1e293b';
        div.style.color = '#f8fafc';
        div.style.boxShadow = '0 10px 25px rgba(0,0,0,0.4)';
    }

    let icon = '<i class="fa-solid fa-circle-check" style="color:#10b981;"></i>';
    if (type === 'error') {
        div.style.borderLeftColor = '#ef4444';
        icon = '<i class="fa-solid fa-circle-xmark" style="color:#ef4444;"></i>';
    } else if (type === 'warning') {
        div.style.borderLeftColor = '#f59e0b';
        icon = '<i class="fa-solid fa-triangle-exclamation" style="color:#f59e0b;"></i>';
    } else if (type === 'info') {
        div.style.borderLeftColor = '#0284c7';
        icon = '<i class="fa-solid fa-circle-info" style="color:#0284c7;"></i>';
    }

    div.innerHTML = `${icon} <span style="flex:1;">${msg}</span>`;
    container.appendChild(div);
    
    // Animate In
    setTimeout(() => div.style.transform = 'translateX(0)', 10);
    
    // Auto Remove
    const remove = () => {
        div.style.transform = 'translateX(130%)';
        div.style.opacity = '0';
        setTimeout(() => div.remove(), 400);
    };
    
    setTimeout(remove, 4500);
    div.onclick = remove;
};

// 2. Loading Overlay System
window.showLoading = function(show = true) {
    let overlay = document.getElementById('global-loading');
    if (!overlay && show) {
        overlay = document.createElement('div');
        overlay.id = 'global-loading';
        overlay.style.cssText = `
            position: fixed; inset: 0; background: rgba(0,0,0,0.5);
            backdrop-filter: blur(4px); z-index: 10000;
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            color: white; font-family: 'Kanit', sans-serif; opacity: 0; transition: opacity 0.3s;
        `;
        overlay.innerHTML = `
            <div style="background:rgba(30,41,59,0.8); padding:30px; border-radius:20px; text-align:center; box-shadow:0 20px 50px rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.1);">
                <i class="fa-solid fa-spinner fa-spin" style="font-size:40px; color:#facc15; margin-bottom:15px;"></i>
                <div style="font-weight:600; font-size:18px;">กำลังดำเนินการ...</div>
                <div style="font-size:13px; opacity:0.7; margin-top:5px;">โปรดรอสักครู่</div>
            </div>
        `;
        document.body.appendChild(overlay);
        setTimeout(() => overlay.style.opacity = '1', 10);
    } else if (overlay && !show) {
        overlay.style.opacity = '0';
        setTimeout(() => overlay.remove(), 300);
    }
};

// DOM Ready Helper for scripts loaded in <head>
function onDomReady(fn) {
    if (document.body && (document.readyState === 'complete' || document.readyState === 'interactive')) {
        fn();
    } else {
        document.addEventListener('DOMContentLoaded', fn);
    }
}

// 3. Scroll to Top Utility
onDomReady(function setupScrollToTop() {
    if (!document.body) return;
    const btn = document.createElement('button');
    btn.id = 'btn-back-to-top';
    btn.innerHTML = '<i class="fa-solid fa-arrow-up"></i>';
    btn.style.cssText = `
        position: fixed; bottom: 85px; right: 25px; width: 45px; height: 45px;
        border-radius: 50%; background: #0284c7; color: white; border: none;
        box-shadow: 0 4px 15px rgba(2,132,199,0.4); cursor: pointer;
        display: none; align-items: center; justify-content: center; z-index: 998;
        transition: all 0.3s;
    `;
    document.body.appendChild(btn);

    window.onscroll = () => {
        if (document.body.scrollTop > 300 || document.documentElement.scrollTop > 300) {
            btn.style.display = 'flex';
        } else {
            btn.style.display = 'none';
        }
    };

    btn.onclick = () => window.scrollTo({ top: 0, behavior: 'smooth' });
});

// 4. Floating Web Chatbot Widget (น้องกิจกรรม Scitech AI)
onDomReady(function setupWebChatbot() {
    if (window.self !== window.top) return;
    if (!document.body) return;

    // Prevent duplicate button creation
    if (document.getElementById('chatbot-toggle-btn')) return;

    // Dynamically inject chatbot.css if not already present
    if (!document.getElementById('chatbot-stylesheet')) {
        const link = document.createElement('link');
        link.id = 'chatbot-stylesheet';
        link.rel = 'stylesheet';
        link.href = 'chatbot.css';
        document.head.appendChild(link);
    }

    // Create Floating Toggle Button
    const toggleBtn = document.createElement('button');
    toggleBtn.id = 'chatbot-toggle-btn';
    toggleBtn.title = 'คุยกับ น้องกิจกรรม Scitech (AI ผู้ช่วย)';
    toggleBtn.innerHTML = `
        <i class="fa-solid fa-robot"></i>
        <span class="chatbot-badge-dot"></span>
    `;
    document.body.appendChild(toggleBtn);

    // Create Chatbot Container
    const container = document.createElement('div');
    container.id = 'chatbot-container';
    container.innerHTML = `
        <div class="chatbot-header">
            <div class="chatbot-header-info">
                <div class="chatbot-avatar"><i class="fa-solid fa-robot"></i></div>
                <div class="chatbot-title-box">
                    <div class="chatbot-title">น้องกิจกรรม Scitech</div>
                    <div class="chatbot-status">
                        <span class="chatbot-status-dot"></span> AI ผู้ช่วยพร้อมตอบคำถาม
                    </div>
                </div>
            </div>
            <button class="chatbot-close-btn" id="chatbot-close-btn" title="ปิดหน้าต่าง"><i class="fa-solid fa-xmark"></i></button>
        </div>
        <div class="chatbot-messages" id="chatbot-messages-list">
            <div class="chat-bubble-row bot">
                <div class="chatbot-avatar" style="width:30px; height:30px; font-size:14px;"><i class="fa-solid fa-robot"></i></div>
                <div class="chat-bubble">🤖 สวัสดีครับ! ผมคือ <strong>น้องกิจกรรม Scitech</strong> ผู้ช่วยอัจฉริยะประจำระบบ<br><br>สามารถสอบถามข้อมูลกิจกรรม, ตรวจสอบคะแนนสะสม หรือวิธีลงทะเบียนได้ทันทีครับ!</div>
            </div>
        </div>
        <div class="chatbot-suggestions" id="chatbot-suggestions-chips">
            <button class="suggestion-chip" data-msg="มีกิจกรรมอะไรบ้าง">📅 กิจกรรมน่าสนใจ</button>
            <button class="suggestion-chip" data-msg="ฉันขาดอีกกี่คะแนนถึงจะจบ">⭐ เช็คเป้าหมายจบการศึกษา</button>
            <button class="suggestion-chip" data-msg="วิธีลงทะเบียนเข้าร่วมกิจกรรม">❓ วิธีลงทะเบียน</button>
        </div>
        <div class="chatbot-input-area">
            <input type="text" class="chatbot-input" id="chatbot-input-text" placeholder="พิมพ์คำถามที่นี่..." autocomplete="off">
            <button class="chatbot-send-btn" id="chatbot-send-action" title="ส่งข้อความ"><i class="fa-solid fa-paper-plane"></i></button>
        </div>
    `;
    document.body.appendChild(container);

    const inputField = document.getElementById('chatbot-input-text');
    const sendBtn = document.getElementById('chatbot-send-action');
    const closeBtn = document.getElementById('chatbot-close-btn');
    const messagesList = document.getElementById('chatbot-messages-list');
    const suggestionsContainer = document.getElementById('chatbot-suggestions-chips');

    // Toggle Chat Modal
    toggleBtn.onclick = () => {
        container.classList.toggle('active');
        if (container.classList.contains('active')) {
            inputField.focus();
            toggleBtn.innerHTML = '<i class="fa-solid fa-chevron-down"></i>';
        } else {
            toggleBtn.innerHTML = '<i class="fa-solid fa-robot"></i><span class="chatbot-badge-dot"></span>';
        }
    };

    closeBtn.onclick = () => {
        container.classList.remove('active');
        toggleBtn.innerHTML = '<i class="fa-solid fa-robot"></i><span class="chatbot-badge-dot"></span>';
    };

    // Mouse Wheel & Drag Horizontal Scroll Helper for Chips
    function enableHorizontalScroll(elem) {
        if (!elem) return;
        elem.addEventListener('wheel', (e) => {
            if (e.deltaY !== 0) {
                e.preventDefault();
                elem.scrollLeft += e.deltaY;
            }
        }, { passive: false });
    }

    enableHorizontalScroll(suggestionsContainer);

    // Quick Suggestion Click Handler
    suggestionsContainer.onclick = (e) => {
        const chip = e.target.closest('.suggestion-chip');
        if (chip) {
            const text = chip.getAttribute('data-msg');
            if (text) sendMessage(text);
        }
    };

    // Send Message Function
    async function sendMessage(customText) {
        const text = (customText || inputField.value).trim();
        if (!text) return;

        // User Bubble
        const userRow = document.createElement('div');
        userRow.className = 'chat-bubble-row user';
        userRow.innerHTML = `<div class="chat-bubble">${escapeHtml(text)}</div>`;
        messagesList.appendChild(userRow);
        
        if (!customText) inputField.value = '';
        autoScroll();

        // Typing Indicator
        const typingRow = document.createElement('div');
        typingRow.className = 'chat-bubble-row bot';
        typingRow.id = 'chatbot-typing-temp';
        typingRow.innerHTML = `
            <div class="chatbot-avatar" style="width:30px; height:30px; font-size:14px;"><i class="fa-solid fa-robot"></i></div>
            <div class="chat-bubble" style="opacity:0.7;"><i class="fa-solid fa-ellipsis fa-bounce"></i> น้องกิจกรรมกำลังพิมพ์...</div>
        `;
        messagesList.appendChild(typingRow);
        autoScroll();

        try {
            const response = await fetch('/api/chatbot/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });
            const data = await response.json();
            
            typingRow.remove();

            const botRow = document.createElement('div');
            botRow.className = 'chat-bubble-row bot';

            if (data.success && data.reply) {
                let formatted = formatMarkdown(data.reply);
                botRow.innerHTML = `
                    <div class="chatbot-avatar" style="width:30px; height:30px; font-size:14px;"><i class="fa-solid fa-robot"></i></div>
                    <div class="chat-bubble">${formatted}</div>
                `;
            } else {
                botRow.innerHTML = `
                    <div class="chatbot-avatar" style="width:30px; height:30px; font-size:14px;"><i class="fa-solid fa-robot"></i></div>
                    <div class="chat-bubble">⚠️ ขออภัย ไม่สามารถดึงข้อมูลได้ในขณะนี้</div>
                `;
            }
            messagesList.appendChild(botRow);

        } catch (error) {
            typingRow.remove();
            const errRow = document.createElement('div');
            errRow.className = 'chat-bubble-row bot';
            errRow.innerHTML = `
                <div class="chatbot-avatar" style="width:30px; height:30px; font-size:14px;"><i class="fa-solid fa-robot"></i></div>
                <div class="chat-bubble">❌ เกิดข้อผิดพลาดในการเชื่อมต่อกับเซิร์ฟเวอร์</div>
            `;
            messagesList.appendChild(errRow);
        }

        autoScroll();
    }

    function autoScroll() {
        messagesList.scrollTop = messagesList.scrollHeight;
    }

    function escapeHtml(str) {
        return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    function formatMarkdown(text) {
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    }

    sendBtn.onclick = () => sendMessage();
    inputField.onkeydown = (e) => {
        if (e.key === 'Enter') sendMessage();
    };

    // 5. Setup Inline Page Chatbot if present on current page
    setTimeout(() => {
        const inlineInput = document.getElementById('inline-chatbot-input');
        const inlineSendBtn = document.getElementById('inline-chatbot-send');
        const inlineMessages = document.getElementById('inline-chatbot-messages');
        const inlineSuggestions = document.getElementById('inline-chatbot-suggestions');

        if (inlineInput && inlineSendBtn && inlineMessages) {
            async function sendInlineMessage(customText) {
                const text = (customText || inlineInput.value).trim();
                if (!text) return;

                const userRow = document.createElement('div');
                userRow.className = 'chat-bubble-row user';
                userRow.innerHTML = `<div class="chat-bubble">${escapeHtml(text)}</div>`;
                inlineMessages.appendChild(userRow);
                
                if (!customText) inlineInput.value = '';
                inlineMessages.scrollTop = inlineMessages.scrollHeight;

                const typingRow = document.createElement('div');
                typingRow.className = 'chat-bubble-row bot';
                typingRow.innerHTML = `
                    <div class="chatbot-avatar" style="width:30px; height:30px; font-size:14px;"><i class="fa-solid fa-robot"></i></div>
                    <div class="chat-bubble" style="opacity:0.7;"><i class="fa-solid fa-ellipsis fa-bounce"></i> น้องกิจกรรมกำลังพิมพ์...</div>
                `;
                inlineMessages.appendChild(typingRow);
                inlineMessages.scrollTop = inlineMessages.scrollHeight;

                try {
                    const response = await fetch('/api/chatbot/ask', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message: text })
                    });
                    const data = await response.json();
                    typingRow.remove();

                    const botRow = document.createElement('div');
                    botRow.className = 'chat-bubble-row bot';
                    if (data.success && data.reply) {
                        botRow.innerHTML = `
                            <div class="chatbot-avatar" style="width:30px; height:30px; font-size:14px;"><i class="fa-solid fa-robot"></i></div>
                            <div class="chat-bubble">${formatMarkdown(data.reply)}</div>
                        `;
                    } else {
                        botRow.innerHTML = `
                            <div class="chatbot-avatar" style="width:30px; height:30px; font-size:14px;"><i class="fa-solid fa-robot"></i></div>
                            <div class="chat-bubble">⚠️ ขออภัย ไม่สามารถดึงข้อมูลได้ในขณะนี้</div>
                        `;
                    }
                    inlineMessages.appendChild(botRow);
                } catch (err) {
                    typingRow.remove();
                    const errRow = document.createElement('div');
                    errRow.className = 'chat-bubble-row bot';
                    errRow.innerHTML = `
                        <div class="chatbot-avatar" style="width:30px; height:30px; font-size:14px;"><i class="fa-solid fa-robot"></i></div>
                        <div class="chat-bubble">❌ เกิดข้อผิดพลาดในการเชื่อมต่อกับเซิร์ฟเวอร์</div>
                    `;
                    inlineMessages.appendChild(errRow);
                }

                inlineMessages.scrollTop = inlineMessages.scrollHeight;
            }

            inlineSendBtn.onclick = () => sendInlineMessage();
            inlineInput.onkeydown = (e) => {
                if (e.key === 'Enter') sendInlineMessage();
            };

            if (inlineSuggestions) {
                enableHorizontalScroll(inlineSuggestions);
                inlineSuggestions.onclick = (e) => {
                    const chip = e.target.closest('.suggestion-chip');
                    if (chip) {
                        const msg = chip.getAttribute('data-msg');
                        if (msg) sendInlineMessage(msg);
                    }
                };
            }
        }
    }, 100);
});

// Navigation Scroll & Toggle Helper
window.scrollToAiSection = function() {
    const btn = document.getElementById('chatbot-toggle-btn');
    const container = document.getElementById('chatbot-container');
    if (container && !container.classList.contains('active')) {
        if (btn) btn.click();
    }
    const section = document.getElementById('ai-assistant-section');
    if (section) {
        section.scrollIntoView({ behavior: 'smooth' });
    }
};



