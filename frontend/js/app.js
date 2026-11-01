/* ==========================================================
   ScholarAI — Phase 4.3
   Navigation, conversation management, API integration,
   message rendering, and toast notifications.
   ========================================================== */

document.addEventListener("DOMContentLoaded", () => {
    const dashboard = document.querySelector(".dashboard-content");
    const breadcrumb = document.querySelector(".breadcrumb");
    const navItems = document.querySelectorAll(".sidebar-nav .nav-item");

    const conversationList = document.getElementById("conversation-list");
    const pinnedList = document.getElementById("pinned-conversations");
    const pinnedGroup = document.getElementById("pinned-conversations-group");
    const emptyHistory = document.getElementById("empty-conversation-history");

    if (!dashboard || !breadcrumb || !navItems.length) {
        console.error("ScholarAI: Required navigation elements were not found.");
        return;
    }

    const overviewHTML = dashboard.innerHTML;

    // ==========================================================
    // TOAST NOTIFICATIONS
    // ==========================================================

    function showToast(message, type = "info", duration = 3000) {
        const container = document.getElementById("toast-container");

        if (!container) {
            console.warn("ScholarAI: Toast container was not found.");
            return null;
        }

        const allowedTypes = ["success", "error", "warning", "info"];

        if (!allowedTypes.includes(type)) {
            type = "info";
        }

        const toast = document.createElement("div");
        toast.className = `toast toast-${type}`;
        toast.setAttribute(
            "role",
            type === "error" ? "alert" : "status"
        );

        const messageElement = document.createElement("span");
        messageElement.className = "toast-message";
        messageElement.textContent = String(message);

        const closeButton = document.createElement("button");
        closeButton.className = "toast-close";
        closeButton.type = "button";
        closeButton.textContent = "\u00D7";
        closeButton.setAttribute("aria-label", "Dismiss notification");

        let removalTimer;
        let animationTimer;

        function removeToast() {
            if (!toast.isConnected) {
                return;
            }

            clearTimeout(removalTimer);
            clearTimeout(animationTimer);

            toast.classList.add("toast-removing");

            animationTimer = setTimeout(() => {
                toast.remove();
            }, 200);
        }

        closeButton.addEventListener("click", removeToast);

        toast.append(messageElement, closeButton);
        container.appendChild(toast);

        if (Number(duration) > 0) {
            removalTimer = setTimeout(removeToast, Number(duration));
        }

        return removeToast;
    }

    // ==========================================================
    // PAGE CONFIGURATION
    // ==========================================================

    const pages = {
        "Overview": {
            description: "Your learning activity at a glance."
        },

        "AI Assistant": {
            description: "Your academic learning companion."
        },

        "My Documents": {
            description: "Manage your academic study materials.",
            message:
                "PDF uploads and document-based question answering will be implemented in the document intelligence phases."
        },

        "Practice & Tests": {
            description: "Prepare, practise, and evaluate your knowledge.",
            message:
                "Practice questions, assessments, and scoring will be developed in upcoming phases."
        },

        "Learning Resources": {
            description: "Discover useful educational materials.",
            message:
                "Educational videos, websites, and learning resources will be integrated in the resource discovery phases."
        },

        "Opportunities": {
            description: "Discover opportunities relevant to your goals.",
            message:
                "Hackathons, internships, and other opportunities will be developed in the live opportunities phase."
        },

        "Learning Progress": {
            description: "Understand your learning activity and progress.",
            message:
                "Learning analytics and progress tracking will be implemented in later phases."
        },

        "Recommendations": {
            description: "Explore learning recommendations tailored to your interests.",
            message:
                "Rule-based, content-based, machine-learning, and hybrid recommendations will be developed in the recommendation phases."
        }
    };

    // ==========================================================
    // CONVERSATION STORAGE
    // ==========================================================

    const STORAGE_KEY = "scholarai-conversations-v1";

    let conversations = [];
    let activeConversationId = null;
    let chatRequestInProgress = false;

    function makeId() {
        return `conversation-${Date.now()}-${Math.random()
            .toString(36)
            .slice(2, 9)}`;
    }

    function escapeHTML(value) {
        return String(value).replace(/[&<>"']/g, character => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        })[character]);
    }
    function renderMarkdown(text) {
    const escaped = escapeHTML(text);
    const lines = escaped.split(/\r?\n/);
    const output = [];

    function inlineMarkdown(value) {
        return value
            .replace(/`([^`]+)`/g, "<code>$1</code>")
            .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
            .replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, "$1<em>$2</em>");
    }

    function isTableRow(line) {
        return /^\s*\|.*\|\s*$/.test(line);
    }

    function isTableSeparator(line) {
        return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line);
    }

    function getCells(line) {
        return line
            .trim()
            .replace(/^\|/, "")
            .replace(/\|$/, "")
            .split("|")
            .map(cell => cell.trim());
    }

    let inCodeBlock = false;
    let codeLines = [];
    let listType = null;
    let paragraph = [];

    function closeList() {
        if (listType) {
            output.push(`</${listType}>`);
            listType = null;
        }
    }

    function flushParagraph() {
        if (paragraph.length) {
            output.push(
                `<p>${inlineMarkdown(paragraph.join(" "))}</p>`
            );
            paragraph = [];
        }
    }

    function renderTable(headerLine, rows) {
        const headers = getCells(headerLine);

        output.push('<div class="chat-table-wrapper"><table>');
        output.push("<thead><tr>");

        headers.forEach(header => {
            output.push(`<th>${inlineMarkdown(header)}</th>`);
        });

        output.push("</tr></thead><tbody>");

        rows.forEach(row => {
            const cells = getCells(row);

            output.push("<tr>");

            headers.forEach((_, index) => {
                output.push(
                    `<td>${inlineMarkdown(cells[index] || "")}</td>`
                );
            });

            output.push("</tr>");
        });

        output.push("</tbody></table></div>");
    }

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const trimmed = line.trim();

        if (trimmed.startsWith("```")) {
            flushParagraph();
            closeList();

            if (inCodeBlock) {
                output.push(
                    `<pre><code>${codeLines.join("\n")}</code></pre>`
                );
                codeLines = [];
                inCodeBlock = false;
            } else {
                inCodeBlock = true;
            }

            continue;
        }

        if (inCodeBlock) {
            codeLines.push(line);
            continue;
        }

        if (
            isTableRow(line) &&
            i + 1 < lines.length &&
            isTableSeparator(lines[i + 1])
        ) {
            flushParagraph();
            closeList();

            const headerLine = line;
            const rows = [];
            i += 2;

            while (i < lines.length && isTableRow(lines[i])) {
                rows.push(lines[i]);
                i++;
            }

            i--;
            renderTable(headerLine, rows);
            continue;
        }

        if (!trimmed) {
            flushParagraph();
            closeList();
            continue;
        }

        const heading = trimmed.match(/^(#{1,3})\s+(.+)$/);

        if (heading) {
            flushParagraph();
            closeList();

            const level = heading[1].length;

            output.push(
                `<h${level}>${inlineMarkdown(heading[2])}</h${level}>`
            );

            continue;
        }

        const unordered = trimmed.match(/^[-*+]\s+(.+)$/);
        const ordered = trimmed.match(/^\d+[.)]\s+(.+)$/);

        if (unordered || ordered) {
            flushParagraph();

            const nextType = unordered ? "ul" : "ol";

            if (listType !== nextType) {
                closeList();
                output.push(`<${nextType}>`);
                listType = nextType;
            }

            const content = unordered
                ? unordered[1]
                : ordered[1];

            output.push(`<li>${inlineMarkdown(content)}</li>`);
            continue;
        }

        paragraph.push(trimmed);
    }

    if (inCodeBlock) {
        output.push(`<pre><code>${codeLines.join("\n")}</code></pre>`);
    }

    flushParagraph();
    closeList();

    return output.join("");
}

    function loadConversations() {
        try {
            const stored = JSON.parse(
                localStorage.getItem(STORAGE_KEY) || "[]"
            );

            conversations = Array.isArray(stored)
                ? stored.filter(item =>
                    item &&
                    typeof item.id === "string" &&
                    typeof item.title === "string" &&
                    Array.isArray(item.messages)
                )
                : [];

        } catch (error) {
            console.warn(
                "ScholarAI: Saved conversations could not be loaded.",
                error
            );

            conversations = [];

            showToast(
                "Saved conversations could not be loaded.",
                "warning",
                5000
            );
        }

        conversations.forEach(conversation => {
            conversation.pinned = Boolean(conversation.pinned);

            conversation.messages = conversation.messages.filter(
                message =>
                    message &&
                    (
                        message.role === "user" ||
                        message.role === "assistant"
                    ) &&
                    typeof message.text === "string"
            );

            conversation.updatedAt =
                Number(conversation.updatedAt) || Date.now();
        });

        conversations.sort((a, b) => b.updatedAt - a.updatedAt);

        activeConversationId = conversations[0]?.id || null;
    }

    function saveConversations() {
        try {
            localStorage.setItem(
                STORAGE_KEY,
                JSON.stringify(conversations)
            );

        } catch (error) {
            console.error(
                "ScholarAI: Conversations could not be saved.",
                error
            );

            showToast(
                "Your conversation could not be saved. Check your browser storage.",
                "error",
                5000
            );
        }
    }

    function getActiveConversation() {
        return conversations.find(
            item => item.id === activeConversationId
        ) || null;
    }

    function createConversation(openAssistant = true) {
        const conversation = {
            id: makeId(),
            title: "New conversation",
            pinned: false,
            createdAt: Date.now(),
            updatedAt: Date.now(),
            messages: []
        };

        conversations.unshift(conversation);
        activeConversationId = conversation.id;

        saveConversations();
        renderConversationHistory();

        if (openAssistant) {
            navigate("AI Assistant");
        }

        return conversation;
    }

    // ==========================================================
    // CONVERSATION HISTORY
    // ==========================================================

    function renderConversationHistory() {
        if (!conversationList || !pinnedList) {
            return;
        }

        const sorted = [...conversations].sort(
            (a, b) => b.updatedAt - a.updatedAt
        );

        const pinned = sorted.filter(item => item.pinned);
        const recent = sorted.filter(item => !item.pinned);

        function itemMarkup(conversation) {
            const active =
                conversation.id === activeConversationId;

            return `
                <div
                    class="conversation-item ${active ? "is-active" : ""}"
                    data-conversation-id="${escapeHTML(conversation.id)}"
                >
                    <button
                        type="button"
                        class="conversation-open"
                        data-conversation-action="open"
                        title="${escapeHTML(conversation.title)}"
                    >
                        <span class="conversation-title">
                            ${escapeHTML(conversation.title)}
                        </span>
                    </button>

                    <div class="conversation-actions">
                        <button
                            type="button"
                            class="conversation-action ${conversation.pinned ? "is-pinned" : ""}"
                            data-conversation-action="pin"
                            aria-label="${conversation.pinned ? "Unpin" : "Pin"} ${escapeHTML(conversation.title)}"
                            title="${conversation.pinned ? "Unpin conversation" : "Pin conversation"}"
                        >
                            ${conversation.pinned ? "📌" : "⌖"}
                        </button>

                        <button
                            type="button"
                            class="conversation-action"
                            data-conversation-action="rename"
                            aria-label="Rename ${escapeHTML(conversation.title)}"
                            title="Rename conversation"
                        >✎</button>

                        <button
                            type="button"
                            class="conversation-action"
                            data-conversation-action="delete"
                            aria-label="Delete ${escapeHTML(conversation.title)}"
                            title="Delete conversation"
                        >×</button>
                    </div>
                </div>
            `;
        }

        pinnedList.innerHTML = pinned.map(itemMarkup).join("");
        conversationList.innerHTML = recent.map(itemMarkup).join("");

        if (pinnedGroup) {
            pinnedGroup.hidden = pinned.length === 0;
        }

        if (emptyHistory) {
            emptyHistory.hidden = sorted.length !== 0;
        }
    }

    // ==========================================================
    // CHAT MESSAGE DISPLAY
    // ==========================================================

   function messageMarkup(conversation) {
    const messages = conversation?.messages || [];

    if (!messages.length) {
        return `
            <div class="chat-empty-state">
                <div class="chat-empty-mark" aria-hidden="true">S</div>
                <h2>What would you like to learn?</h2>
                <p>Ask a study question to start a conversation.</p>

                <div class="chat-suggestions">
                    <button type="button" class="suggestion-chip"
                        data-prompt="Explain a difficult concept in simple terms">
                        Explain a concept
                    </button>

                    <button type="button" class="suggestion-chip"
                        data-prompt="Help me create a study plan">
                        Create a study plan
                    </button>

                    <button type="button" class="suggestion-chip"
                        data-prompt="Give me practice questions for a topic">
                        Practise a topic
                    </button>
                </div>
            </div>
        `;
    }

    return messages.map((message, index) => `
        <article class="chat-message ${
            message.role === "user"
                ? "user-message"
                : "assistant-message"
        }">
            <div class="chat-message-avatar" aria-hidden="true">
                ${message.role === "user" ? "S" : "AI"}
            </div>

            <div class="chat-message-content">
                <p class="chat-message-role">
                    ${message.role === "user" ? "You" : "ScholarAI"}
                </p>

                <div class="chat-message-text">${
                    renderMarkdown(message.text)
                }</div>

                <div class="chat-message-actions">
                    <button
                        type="button"
                        class="copy-message-button"
                        data-copy-message-index="${index}"
                        data-copy-conversation-id="${escapeHTML(conversation.id)}"
                        aria-label="Copy this message"
                        title="Copy message"
                    >
                        <span aria-hidden="true">▢</span>
                        Copy
                    </button>
                </div>
            </div>
        </article>
    `).join("");
}
    // ==========================================================
    // AI ASSISTANT PAGE
    // ==========================================================

    function renderAssistant() {
        let conversation = getActiveConversation();

        if (!conversation) {
            conversation = createConversation(false);
        }

        dashboard.innerHTML = `
            <section class="assistant-page" aria-label="AI Assistant">
                <header class="assistant-page-header">
                    <div>
                        <p class="assistant-eyebrow">YOUR STUDY COMPANION</p>
                        <h1>AI Assistant</h1>
                        <p class="assistant-subtitle">
                            ${escapeHTML(conversation.title)}
                        </p>
                    </div>

                    <div class="assistant-header-actions">
                        <button
                            class="secondary-chat-button"
                            id="rename-active-conversation"
                            type="button"
                        >
                            Rename
                        </button>

                        <button
                            class="clear-chat-button"
                            id="clear-chat"
                            type="button"
                            ${conversation.messages.length ? "" : "disabled"}
                        >
                            Clear chat
                        </button>
                    </div>
                </header>

                <div class="chat-workspace">
                    <div
                        class="chat-messages"
                        id="chat-messages"
                        aria-live="polite"
                    >
                        ${messageMarkup(conversation)}
                    </div>

                    <form class="assistant-composer" id="assistant-chat-form">
                        <label
                            class="visually-hidden"
                            for="assistant-chat-input"
                        >
                            Message ScholarAI
                        </label>

                        <textarea
                            id="assistant-chat-input"
                            name="message"
                            rows="1"
                            maxlength="4000"
                            placeholder="Ask anything about your studies..."
                            required
                        ></textarea>

                        <div class="composer-bottom">
                            <span class="composer-note">
                                Enter to send · Shift+Enter for a new line
                            </span>

                            <button
                                class="composer-send-button"
                                type="submit"
                                aria-label="Send message"
                            >
                                ↑
                            </button>
                        </div>
                    </form>

                    <p class="assistant-disclaimer">
                        Preview interface · Messages are stored in this browser only.
                        Live AI responses will be connected in Phase 5.
                    </p>
                </div>
            </section>
        `;

        const list = document.getElementById("chat-messages");

        if (list) {
            list.scrollTop = list.scrollHeight;
        }
    }

    // ==========================================================
    // PLACEHOLDER PAGES
    // ==========================================================

    function renderPlaceholder(name) {
        const page = pages[name];

        dashboard.innerHTML = `
            <section class="navigation-page">
                <div class="navigation-page-heading">
                    <p class="navigation-page-eyebrow">SCHOLARAI WORKSPACE</p>
                    <h1>${escapeHTML(name)}</h1>

                    <p class="navigation-page-description">
                        ${escapeHTML(page.description)}
                    </p>
                </div>

                <article class="navigation-placeholder-card">
                    <div
                        class="navigation-placeholder-icon"
                        aria-hidden="true"
                    >S</div>

                    <h2>${escapeHTML(name)}</h2>

                    <p>${escapeHTML(
                        page.message ||
                        "This feature will be implemented in a later roadmap phase."
                    )}</p>

                    <span class="navigation-status">
                        Feature development in progress
                    </span>
                </article>
            </section>
        `;
    }

    // ==========================================================
    // NAVIGATION
    // ==========================================================

    function navigate(name, push = true) {
        if (!pages[name]) {
            name = "Overview";
        }

        if (name === "Overview") {
            dashboard.innerHTML = overviewHTML;
        } else if (name === "AI Assistant") {
            renderAssistant();
        } else {
            renderPlaceholder(name);
        }

        navItems.forEach(item => {
            const label = item.querySelector("span:nth-child(2)");
            const active = label && label.textContent.trim() === name;

            item.classList.toggle("active", Boolean(active));

            if (active) {
                item.setAttribute("aria-current", "page");
            } else {
                item.removeAttribute("aria-current");
            }
        });

        breadcrumb.innerHTML =
            `Workspace <span>/</span> ${escapeHTML(name)}`;

        if (push) {
            const url = new URL(window.location.href);
            url.hash = encodeURIComponent(name);

            history.pushState({ page: name }, "", url);
        }

        window.scrollTo({ top: 0, behavior: "smooth" });
    }

    // ==========================================================
    // ADD AND SAVE MESSAGES
    // ==========================================================

    function addMessage(role, text) {
        let conversation = getActiveConversation();

        if (!conversation) {
            conversation = createConversation(false);
        }

        conversation.messages.push({
            role,
            text,
            timestamp: Date.now()
        });

        conversation.updatedAt = Date.now();

        const firstUserMessage = conversation.messages.find(
            item => item.role === "user"
        );

        if (
            firstUserMessage &&
            conversation.title === "New conversation"
        ) {
            conversation.title = firstUserMessage.text
                .replace(/\s+/g, " ")
                .trim()
                .slice(0, 38) || "New conversation";

            if (firstUserMessage.text.trim().length > 38) {
                conversation.title =
                    conversation.title.trimEnd() + "…";
            }
        }

        conversations.sort((a, b) => b.updatedAt - a.updatedAt);

        saveConversations();
        renderConversationHistory();
    }

    // ==========================================================
    // SEND CHAT MESSAGE — PHASE 4.3
    // ==========================================================

    async function sendChat(form) {
        if (chatRequestInProgress) {
            return;
        }

        const input = form.querySelector("#assistant-chat-input");
        const text = input?.value.trim();

        if (!text) {
            showToast("Please enter a message before sending.", "warning");
            input?.focus();
            return;
        }

        if (text.length > 5000) {
            showToast(
                "Your message must contain no more than 5000 characters.",
                "warning"
            );
            input?.focus();
            return;
        }

        if (!window.ScholarAIAPI) {
            showToast(
                "The ScholarAI API client failed to load. Refresh the page and try again.",
                "error"
            );
            return;
        }

        const conversation = getActiveConversation();

        if (!conversation) {
            showToast(
                "Unable to find the active conversation. Please start a new conversation.",
                "error"
            );
            return;
        }

        const conversationId = conversation.id;
        chatRequestInProgress = true;

        try {
            // Save the user's message exactly once.
            addMessage("user", text);

            // Render the question before requesting the backend.
            renderAssistant();

            const currentInput = document.getElementById(
                "assistant-chat-input"
            );

            const sendButton = document.querySelector(
                "#assistant-chat-form .composer-send-button"
            );

            const messageList = document.getElementById("chat-messages");

            if (currentInput) {
                currentInput.disabled = true;
            }

            if (sendButton) {
                sendButton.disabled = true;
                sendButton.setAttribute("aria-busy", "true");
            }

            const loading = document.createElement("div");
            loading.className = "chat-loading";
            loading.id = "chat-loading";
            loading.setAttribute("role", "status");
            loading.setAttribute("aria-live", "polite");

            loading.innerHTML = `
                <span>ScholarAI is preparing a response</span>
                <span class="chat-loading-dots" aria-hidden="true">
                    <span></span>
                    <span></span>
                    <span></span>
                </span>
            `;

            messageList?.appendChild(loading);

            if (messageList) {
                messageList.scrollTop = messageList.scrollHeight;
            }

            // Send the request to FastAPI.
            const response = await window.ScholarAIAPI.sendChatMessage(
                text,
                conversationId
            );

            // Avoid displaying a response in another conversation.
            const stillActive = getActiveConversation();

            if (!stillActive || stillActive.id !== conversationId) {
                return;
            }

            if (
                typeof response?.answer !== "string" ||
                !response.answer.trim()
            ) {
                throw new Error("The backend returned an empty answer.");
            }

            // Save the assistant's answer.
            addMessage("assistant", response.answer);

            // Render the question and answer in the conversation.
            renderAssistant();

            const chatMessages = document.getElementById("chat-messages");

            

console.log("Answer saved:", response.answer);
console.log("Chat container found:", Boolean(chatMessages));
console.log(
    "Chat container HTML:",
    chatMessages?.innerHTML
);

console.log(
    "All visible assistant answers:",
    [...document.querySelectorAll(".assistant-message")]
        .map(message => message.innerText)
);

console.log(
    "All chat message elements:",
    document.querySelectorAll("#chat-messages .chat-message").length
);
console.log(
    "Assistant message count:",
    chatMessages?.querySelectorAll(".assistant-message").length
);
console.log(
    "User message count:",
    chatMessages?.querySelectorAll(".user-message").length
);
            const updatedMessageList =
                document.getElementById("chat-messages");

            if (updatedMessageList) {
                updatedMessageList.scrollTop =
                    updatedMessageList.scrollHeight;
            }

            showToast(
                "Response received from the backend.",
                "success",
                1800
            );

        } catch (error) {
            console.error("ScholarAI chat request failed:", error);

            showToast(
                error.message || "Something went wrong. Please try again.",
                "error",
                5000
            );

        } finally {
            chatRequestInProgress = false;

            document.getElementById("chat-loading")?.remove();

            const currentInput = document.getElementById(
                "assistant-chat-input"
            );

            const sendButton = document.querySelector(
                "#assistant-chat-form .composer-send-button"
            );

            if (currentInput) {
                currentInput.disabled = false;
            }

            if (sendButton) {
                sendButton.disabled = false;
                sendButton.removeAttribute("aria-busy");
            }
        }
    }

    // ==========================================================
    // RENAME CONVERSATION
    // ==========================================================

    function renameConversation(conversation) {
        const proposed = window.prompt(
            "Enter a new conversation title:",
            conversation.title
        );

        if (proposed === null) {
            return;
        }

        const title = proposed.trim();

        if (!title) {
            showToast(
                "Conversation title cannot be empty.",
                "warning"
            );
            return;
        }

        conversation.title = title.slice(0, 80);
        conversation.updatedAt = Date.now();

        saveConversations();
        renderConversationHistory();

        if (conversation.id === activeConversationId) {
            renderAssistant();
        }

        showToast("Conversation renamed successfully.", "success");
    }

    // ==========================================================
    // DELETE CONVERSATION
    // ==========================================================

    function deleteConversation(conversation) {
        const confirmed = window.confirm(
            `Delete "${conversation.title}"? This cannot be undone.`
        );

        if (!confirmed) {
            return;
        }

        conversations = conversations.filter(
            item => item.id !== conversation.id
        );

        if (activeConversationId === conversation.id) {
            activeConversationId = conversations[0]?.id || null;
        }

        saveConversations();
        renderConversationHistory();

        if (document.querySelector(".assistant-page")) {
            if (activeConversationId) {
                renderAssistant();
            } else {
                createConversation(false);
                renderAssistant();
            }
        }

        showToast("Conversation deleted successfully.", "success");
    }

    // ==========================================================
    // DASHBOARD CARD DESTINATIONS
    // ==========================================================

    const cardDestinations = {
        "Study with AI": "AI Assistant",
        "My documents": "My Documents",
        "Test your knowledge": "Practice & Tests",
        "Discover resources": "Learning Resources",
        "Explore opportunities": "Opportunities",
        "Track your growth": "Learning Progress"
    };

    function getCardDestination(card) {
        const text = card.textContent
            .replace(/\s+/g, " ")
            .trim()
            .toLowerCase();

        for (const [label, destination] of Object.entries(
            cardDestinations
        )) {
            if (text.includes(label.toLowerCase())) {
                return destination;
            }
        }

        return null;
    }
// ==========================================================
// COPY CHAT MESSAGE
// ==========================================================

async function copyMessage(copyButton) {
    const conversationId =
        copyButton.dataset.copyConversationId;

    const messageIndex =
        Number(copyButton.dataset.copyMessageIndex);

    const conversation = conversations.find(
        item => item.id === conversationId
    );

    const message = conversation?.messages[messageIndex];

    if (!message || typeof message.text !== "string") {
        showToast("Unable to find this message.", "error");
        return;
    }

    const textToCopy = message.text;

    try {
        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(textToCopy);
        } else {
            const temporaryInput = document.createElement("textarea");

            temporaryInput.value = textToCopy;
            temporaryInput.setAttribute("readonly", "");
            temporaryInput.style.position = "fixed";
            temporaryInput.style.left = "-9999px";

            document.body.appendChild(temporaryInput);
            temporaryInput.select();

            const copied = document.execCommand("copy");
            temporaryInput.remove();

            if (!copied) {
                throw new Error("Clipboard copy failed.");
            }
        }

        const originalHTML = copyButton.innerHTML;

        copyButton.innerHTML =
            '<span aria-hidden="true">✓</span> Copied';

        copyButton.classList.add("is-copied");

        showToast("Message copied to clipboard.", "success", 1800);

        window.setTimeout(() => {
            if (copyButton.isConnected) {
                copyButton.innerHTML = originalHTML;
                copyButton.classList.remove("is-copied");
            }
        }, 1600);

    } catch (error) {
        console.error("ScholarAI: Could not copy message.", error);

        showToast(
            "Could not copy the message. Please try again.",
            "error"
        );
    }
}
    // ==========================================================
    // CLICK EVENTS
    // ==========================================================

    document.addEventListener("click", async event => {
    const copyButton = event.target.closest(
        "[data-copy-message-index]"
    );

    if (copyButton) {
        await copyMessage(copyButton);
        return;
    }
        const nav = event.target.closest(
            ".sidebar-nav .nav-item"
        );

        if (nav) {
            event.preventDefault();

            const label = nav.querySelector("span:nth-child(2)");
            const pageName = label?.textContent.trim();

            if (pageName && pages[pageName]) {
                navigate(pageName);
            }

            return;
        }

        const card = event.target.closest(
            ".action-card, .discovery-card"
        );

        if (card) {
            const destination = getCardDestination(card);

            if (destination) {
                navigate(destination);
            }

            return;
        }

        const historyAction = event.target.closest(
            "[data-conversation-action]"
        );

        if (historyAction) {
            const row = historyAction.closest(
                "[data-conversation-id]"
            );

            const conversation = conversations.find(
                item => item.id === row?.dataset.conversationId
            );

            if (!conversation) {
                showToast(
                    "This conversation could not be found.",
                    "error"
                );
                return;
            }

            const action = historyAction.dataset.conversationAction;

            if (action === "open") {
                activeConversationId = conversation.id;
                renderConversationHistory();
                navigate("AI Assistant");

            } else if (action === "pin") {
                conversation.pinned = !conversation.pinned;
                conversation.updatedAt = Date.now();

                saveConversations();
                renderConversationHistory();

                showToast(
                    conversation.pinned
                        ? "Conversation pinned."
                        : "Conversation unpinned.",
                    "success"
                );

            } else if (action === "rename") {
                renameConversation(conversation);

            } else if (action === "delete") {
                deleteConversation(conversation);
            }

            return;
        }

        if (event.target.closest("#new-conversation")) {
            createConversation(true);
            showToast("New conversation created.", "success");
            return;
        }

        if (event.target.closest("#rename-active-conversation")) {
            const conversation = getActiveConversation();

            if (conversation) {
                renameConversation(conversation);
            }

            return;
        }

        const suggestion = event.target.closest(".suggestion-chip");

        if (suggestion) {
            const input = document.getElementById(
                "assistant-chat-input"
            );

            if (input) {
                input.value = suggestion.dataset.prompt || "";
                input.focus();
            }

            return;
        }

        if (event.target.closest("#clear-chat")) {
            const conversation = getActiveConversation();

            if (!conversation) {
                showToast(
                    "There is no active conversation to clear.",
                    "warning"
                );
                return;
            }

            if (!window.confirm("Clear all messages in this conversation?")) {
                return;
            }

            conversation.messages = [];
            conversation.title = "New conversation";
            conversation.updatedAt = Date.now();

            saveConversations();
            renderConversationHistory();
            renderAssistant();

            showToast("Conversation messages cleared.", "success");
        }
    });

    // ==========================================================
    // KEYBOARD ACCESSIBILITY FOR DASHBOARD CARDS
    // ==========================================================

    document.addEventListener("keydown", event => {
        if (event.key !== "Enter" && event.key !== " ") {
            return;
        }

        const card = event.target.closest(
            ".action-card, .discovery-card"
        );

        if (!card) {
            return;
        }

        if (
            event.target !== card &&
            event.target.closest(
                "a, button, input, textarea, select"
            )
        ) {
            return;
        }

        event.preventDefault();
        card.click();
    });

    // ==========================================================
    // FORM SUBMISSION
    // ==========================================================

    document.addEventListener("submit", event => {
        if (event.target.id === "assistant-chat-form") {
            event.preventDefault();
            void sendChat(event.target);
            return;
        }

        if (event.target.matches(".chat-search")) {
            event.preventDefault();

            const input = event.target.querySelector(
                'input[name="q"]'
            );

            const question = input?.value.trim();

            if (!question) {
                showToast(
                    "Please enter a question in the search bar.",
                    "warning"
                );
                input?.focus();
                return;
            }

            if (question.length > 5000) {
                showToast(
                    "Your question must contain no more than 5000 characters.",
                    "warning"
                );
                input?.focus();
                return;
            }

            let conversation = getActiveConversation();

            if (!conversation || conversation.messages.length > 0) {
                conversation = createConversation(false);
            }

            navigate("AI Assistant");

            const assistantInput = document.getElementById(
                "assistant-chat-input"
            );

            const assistantForm = document.getElementById(
                "assistant-chat-form"
            );

            if (!assistantInput || !assistantForm) {
                showToast(
                    "Unable to open the assistant. Please try again.",
                    "error"
                );
                return;
            }

            assistantInput.value = question;
            assistantForm.requestSubmit();
        }
    });

    // ==========================================================
    // ENTER TO SEND; SHIFT+ENTER FOR A NEW LINE
    // ==========================================================

    document.addEventListener("keydown", event => {
        if (
            event.target.id === "assistant-chat-input" &&
            event.key === "Enter" &&
            !event.shiftKey &&
            !event.isComposing
        ) {
            event.preventDefault();

            const form = event.target.form;

            if (form) {
                form.requestSubmit();
            }
        }
    });

    // ==========================================================
    // BROWSER BACK/FORWARD NAVIGATION
    // ==========================================================

    window.addEventListener("popstate", event => {
        let hashName = "Overview";

        try {
            hashName = window.location.hash
                ? decodeURIComponent(window.location.hash.slice(1))
                : "Overview";
        } catch (error) {
            hashName = "Overview";
        }

        const name = event.state?.page || hashName;

        navigate(pages[name] ? name : "Overview", false);
    });

    // ==========================================================
    // INITIALIZE APPLICATION
    // ==========================================================

    loadConversations();
    renderConversationHistory();

    let initialHash = "Overview";

    try {
        initialHash = window.location.hash
            ? decodeURIComponent(window.location.hash.slice(1))
            : "Overview";
    } catch (error) {
        initialHash = "Overview";
    }

    const initialPage = history.state?.page || initialHash;

    navigate(pages[initialPage] ? initialPage : "Overview", false);

    console.log("ScholarAI Phase 4.3 initialized.");

    // ==========================================================
    // NOTIFICATION TEST HELPER
    // ==========================================================

    window.scholarAIToastTest = function () {
        showToast(
            "ScholarAI notification system is working!",
            "success"
        );
    };
});