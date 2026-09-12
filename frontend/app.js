const API_BASE_URL = "http://127.0.0.1:8000";

let currentUser = null;
let authToken = localStorage.getItem("enterpriseiq_token") || "";


// ============================================================
// HELPER
// ============================================================

function $(id) {
    return document.getElementById(id);
}


// ============================================================
// API REQUEST
// ============================================================

async function apiRequest(endpoint, options = {}) {

    const headers = {
        ...(options.headers || {})
    };

    if (authToken) {
        headers["Authorization"] = `Bearer ${authToken}`;
    }

    if (
        options.body &&
        !(options.body instanceof FormData)
    ) {
        headers["Content-Type"] = "application/json";
    }

    const response = await fetch(
        `${API_BASE_URL}${endpoint}`,
        {
            ...options,
            headers
        }
    );

    let data = null;

    try {
        data = await response.json();
    } catch {
        data = null;
    }

    if (!response.ok) {

        let message = "Request failed.";

        if (data) {

            if (typeof data.detail === "string") {
                message = data.detail;
            } else if (data.message) {
                message = data.message;
            }
        }

        const error = new Error(message);
        error.status = response.status;

        throw error;
    }

    return data;
}


// ============================================================
// AUTH SCREEN
// ============================================================

function showAuthScreen() {

    const authScreen = $("authScreen");
    const appScreen = $("appScreen");

    if (authScreen) {
        authScreen.classList.remove("hidden");
    }

    if (appScreen) {
        appScreen.classList.add("hidden");
    }
}


function showAppScreen() {

    const authScreen = $("authScreen");
    const appScreen = $("appScreen");

    if (authScreen) {
        authScreen.classList.add("hidden");
    }

    if (appScreen) {
        appScreen.classList.remove("hidden");
    }
}


// ============================================================
// LOGIN / REGISTER SWITCH
// ============================================================

function showRegister() {

    const loginForm = $("loginForm");
    const registerForm = $("registerForm");

    if (loginForm) {
        loginForm.classList.add("hidden");
    }

    if (registerForm) {
        registerForm.classList.remove("hidden");
    }

    clearMessage($("loginMessage"));
    clearMessage($("registerMessage"));
}


function showLogin() {

    const loginForm = $("loginForm");
    const registerForm = $("registerForm");

    if (registerForm) {
        registerForm.classList.add("hidden");
    }

    if (loginForm) {
        loginForm.classList.remove("hidden");
    }

    clearMessage($("loginMessage"));
    clearMessage($("registerMessage"));
}


// ============================================================
// CURRENT USER
// ============================================================

async function loadCurrentUser() {

    if (!authToken) {
        showAuthScreen();
        return;
    }

    try {

        currentUser = await apiRequest(
            "/api/auth/me"
        );

        showAppScreen();

        updateUserUI();

        showPage("dashboard");

        await checkBackendHealth();

        await loadDocuments();

    } catch (error) {

        console.error(
            "Authentication failed:",
            error
        );

        logout();
    }
}


// ============================================================
// USER UI
// ============================================================

function updateUserUI() {

    if (!currentUser) {
        return;
    }

    const name =
        currentUser.full_name ||
        currentUser.email ||
        "User";

    const role =
        currentUser.role ||
        "user";

    const nameElements = [
        $("welcomeUser"),
        $("sidebarUserName"),
        $("topUserName")
    ];

    nameElements.forEach(
        element => {

            if (element) {
                element.textContent = name;
            }
        }
    );

    const roleElement = $("sidebarUserRole");

    if (roleElement) {
        roleElement.textContent = role;
    }

    const avatar = $("userAvatar");

    if (avatar) {
        avatar.textContent =
            name.charAt(0).toUpperCase();
    }

    const adminNav = $("adminNav");

    if (adminNav) {

        if (role === "admin") {

            adminNav.classList.remove("hidden");

        } else {

            adminNav.classList.add("hidden");
        }
    }
}


// ============================================================
// LOGOUT
// ============================================================

function logout() {

    authToken = "";
    currentUser = null;

    localStorage.removeItem(
        "enterpriseiq_token"
    );

    showAuthScreen();
    showLogin();
}


// ============================================================
// LOGIN
// ============================================================

async function login() {

    const emailInput = $("loginEmail");
    const passwordInput = $("loginPassword");
    const message = $("loginMessage");
    const button = $("loginButton");

    const email =
        emailInput
            ? emailInput.value.trim()
            : "";

    const password =
        passwordInput
            ? passwordInput.value
            : "";

    if (!email || !password) {

        showMessage(
            message,
            "Please enter email and password.",
            "error"
        );

        return;
    }

    if (button) {

        button.disabled = true;
        button.textContent = "Logging in...";
    }

    clearMessage(message);

    try {

        const data = await apiRequest(
            "/api/auth/login",
            {
                method: "POST",
                body: JSON.stringify({
                    email,
                    password
                })
            }
        );

        authToken = data.access_token;

        localStorage.setItem(
            "enterpriseiq_token",
            authToken
        );

        currentUser = await apiRequest(
            "/api/auth/me"
        );

        showAppScreen();

        updateUserUI();

        showPage("dashboard");

        await checkBackendHealth();

        await loadDocuments();

    } catch (error) {

        console.error(
            "Login failed:",
            error
        );

        showMessage(
            message,
            error.message,
            "error"
        );

    } finally {

        if (button) {

            button.disabled = false;
            button.textContent = "Login";
        }
    }
}


// ============================================================
// REGISTER
// ============================================================

async function register() {

    const nameInput = $("registerName");
    const emailInput = $("registerEmail");
    const passwordInput = $("registerPassword");
    const message = $("registerMessage");
    const button = $("registerButton");

    const fullName =
        nameInput
            ? nameInput.value.trim()
            : "";

    const email =
        emailInput
            ? emailInput.value.trim()
            : "";

    const password =
        passwordInput
            ? passwordInput.value
            : "";

    if (
        !fullName ||
        !email ||
        !password
    ) {

        showMessage(
            message,
            "Please fill all fields.",
            "error"
        );

        return;
    }

    if (password.length < 8) {

        showMessage(
            message,
            "Password must contain at least 8 characters.",
            "error"
        );

        return;
    }

    if (button) {

        button.disabled = true;
        button.textContent = "Creating...";
    }

    clearMessage(message);

    try {

        await apiRequest(
            "/api/auth/register",
            {
                method: "POST",
                body: JSON.stringify({
                    full_name: fullName,
                    email,
                    password
                })
            }
        );

        showMessage(
            message,
            "Registration successful. Please login.",
            "success"
        );

        if ($("loginEmail")) {
            $("loginEmail").value = email;
        }

        if ($("loginPassword")) {
            $("loginPassword").value = "";
        }

        setTimeout(
            () => {
                showLogin();
            },
            800
        );

    } catch (error) {

        console.error(
            "Registration failed:",
            error
        );

        showMessage(
            message,
            error.message,
            "error"
        );

    } finally {

        if (button) {

            button.disabled = false;
            button.textContent = "Create Account";
        }
    }
}


// ============================================================
// MESSAGE HELPERS
// ============================================================

function showMessage(
    element,
    text,
    type = "info"
) {

    if (!element) {
        return;
    }

    element.textContent = text;

    element.className =
        `auth-message ${type}`;
}


function clearMessage(element) {

    if (!element) {
        return;
    }

    element.textContent = "";

    element.className =
        "auth-message";
}


// ============================================================
// PAGE NAVIGATION
// ============================================================

function showPage(pageName) {

    const pages =
        document.querySelectorAll(".page");

    pages.forEach(
        page => {
            page.classList.remove(
                "active-page"
            );
        }
    );

    const target =
        $(`${pageName}Page`);

    if (!target) {
        return;
    }

    target.classList.add(
        "active-page"
    );

    const navItems =
        document.querySelectorAll(
            "[data-page]"
        );

    navItems.forEach(
        item => {

            if (
                item.dataset.page === pageName
            ) {

                item.classList.add("active");

            } else {

                item.classList.remove("active");
            }
        }
    );

    updatePageHeader(pageName);

    if (pageName === "documents") {
        loadDocuments();
    }

    if (pageName === "evaluations") {
        loadEvaluationDashboard();
    }

    if (pageName === "admin") {

        if (
            currentUser &&
            currentUser.role === "admin"
        ) {
            loadUsers();
        }
    }
}


// ============================================================
// PAGE HEADER
// ============================================================

function updatePageHeader(pageName) {

    const pageConfig = {

        dashboard: {
            title: "Dashboard",
            subtitle:
                "Enterprise intelligence at your fingertips."
        },

        chat: {
            title: "Agentic Chat",
            subtitle:
                "Ask questions across enterprise documents and data."
        },

        documents: {
            title: "Documents",
            subtitle:
                "Upload and manage your enterprise documents."
        },

        evaluations: {
            title: "Evaluation",
            subtitle:
                "Current EnterpriseIQ evaluation performance."
        },

        admin: {
            title: "Admin",
            subtitle:
                "Manage EnterpriseIQ users."
        }
    };

    const config =
        pageConfig[pageName];

    if (!config) {
        return;
    }

    const title =
        $("pageTitle");

    const subtitle =
        $("pageSubtitle");

    if (title) {
        title.textContent =
            config.title;
    }

    if (subtitle) {
        subtitle.textContent =
            config.subtitle;
    }
}


// ============================================================
// BACKEND HEALTH
// ============================================================

async function checkBackendHealth() {

    const status =
        $("backendStatus");

    try {

        const response =
            await fetch(
                `${API_BASE_URL}/health`
            );

        if (!response.ok) {
            throw new Error(
                "Backend unavailable"
            );
        }

        await response.json();

        if (status) {

            status.classList.remove("error");
            status.classList.add("connected");

            status.innerHTML = `
                <span class="status-dot"></span>
                Backend Online
            `;
        }

    } catch (error) {

        console.error(
            "Backend health error:",
            error
        );

        if (status) {

            status.classList.remove("connected");
            status.classList.add("error");

            status.innerHTML = `
                <span class="status-dot"></span>
                Backend Offline
            `;
        }
    }
}


// ============================================================
// CHAT EXAMPLES
// ============================================================

function useExample(question) {

    const input =
        $("chatInput");

    if (!input) {
        return;
    }

    input.value =
        question;

    input.focus();
}


// ============================================================
// CLEAR CHAT
// ============================================================

function clearChat() {

    const messages =
        $("chatMessages");

    if (!messages) {
        return;
    }

    messages.innerHTML = `
        <div
            id="chatEmpty"
            class="chat-empty"
        >

            <div class="chat-empty-icon">
                ✦
            </div>

            <h2>
                Ask EnterpriseIQ
            </h2>

            <p>
                Ask questions about your
                enterprise documents and data.
            </p>

            <div class="example-questions">

                <button
                    onclick="useExample('What is the payment due date for Rahul Enterprises?')"
                >
                    What is the payment due date
                    for Rahul Enterprises?
                </button>

                <button
                    onclick="useExample('What is the total sales for Q2 2026?')"
                >
                    What is the total sales
                    for Q2 2026?
                </button>

                <button
                    onclick="useExample('What is the maximum standard discount allowed?')"
                >
                    What is the maximum
                    standard discount allowed?
                </button>

            </div>

        </div>
    `;
}


// ============================================================
// ADD USER MESSAGE
// ============================================================

function addUserMessage(text) {

    const messages =
        $("chatMessages");

    if (!messages) {
        return;
    }

    const empty =
        $("chatEmpty");

    if (empty) {
        empty.remove();
    }

    const wrapper =
        document.createElement("div");

    wrapper.className =
        "chat-message user-message";

    const label =
        document.createElement("div");

    label.className =
        "chat-message-label";

    label.textContent =
        "You";

    const bubble =
        document.createElement("div");

    bubble.className =
        "chat-bubble user";

    bubble.textContent =
        text;

    wrapper.appendChild(label);
    wrapper.appendChild(bubble);

    messages.appendChild(wrapper);

    messages.scrollTop =
        messages.scrollHeight;
}


// ============================================================
// ADD ERROR MESSAGE
// ============================================================

function addErrorMessage(text) {

    const messages =
        $("chatMessages");

    if (!messages) {
        return;
    }

    const wrapper =
        document.createElement("div");

    wrapper.className =
        "chat-message assistant-message";

    const label =
        document.createElement("div");

    label.className =
        "chat-message-label";

    label.textContent =
        "EnterpriseIQ";

    const bubble =
        document.createElement("div");

    bubble.className =
        "chat-bubble error";

    bubble.textContent =
        text;

    wrapper.appendChild(label);
    wrapper.appendChild(bubble);

    messages.appendChild(wrapper);

    messages.scrollTop =
        messages.scrollHeight;
}


// ============================================================
// LOADING MESSAGE
// ============================================================

function addLoadingMessage() {

    const messages =
        $("chatMessages");

    if (!messages) {
        return null;
    }

    const wrapper =
        document.createElement("div");

    wrapper.className =
        "chat-message assistant-message";

    wrapper.id =
        "agentLoadingWrapper";

    const label =
        document.createElement("div");

    label.className =
        "chat-message-label";

    label.textContent =
        "EnterpriseIQ";

    const bubble =
        document.createElement("div");

    bubble.className =
        "chat-bubble assistant";

    bubble.id =
        "agentLoading";

    bubble.innerHTML = `
        <span>EnterpriseIQ is thinking</span>
        <span class="thinking-dots">...</span>
    `;

    wrapper.appendChild(label);
    wrapper.appendChild(bubble);

    messages.appendChild(wrapper);

    messages.scrollTop =
        messages.scrollHeight;

    return wrapper;
}


function removeLoadingMessage() {

    const loading =
        $("agentLoadingWrapper");

    if (loading) {
        loading.remove();
    }
}


// ============================================================
// CLEAN SOURCE LIST
// ============================================================

function getUniqueSources(sources) {

    if (!Array.isArray(sources)) {
        return [];
    }

    const seen =
        new Set();

    const unique =
        [];

    sources.forEach(
        source => {

            if (!source) {
                return;
            }

            const filename =
                source.filename ||
                "Unknown document";

            const page =
                source.page_number !== null &&
                source.page_number !== undefined
                    ? source.page_number
                    : null;

            const key =
                `${filename}|${page}`;

            if (!seen.has(key)) {

                seen.add(key);

                unique.push({
                    filename,
                    page_number: page
                });
            }
        }
    );

    return unique;
}


// ============================================================
// FORMAT TOOL NAME
// ============================================================

function formatToolName(tool) {

    if (!tool) {
        return "";
    }

    return tool
        .replace(/_/g, " ")
        .replace(
            /\b\w/g,
            character =>
                character.toUpperCase()
        );
}


// ============================================================
// FORMAT TOOLS
// ============================================================

function formatTools(tools) {

    if (!Array.isArray(tools)) {
        return "";
    }

    const validTools =
        tools.filter(Boolean);

    return validTools
        .map(formatToolName)
        .join(" → ");
}


// ============================================================
// ESCAPE HTML
// ============================================================

function escapeHtml(text) {

    const div =
        document.createElement("div");

    div.textContent =
        text;

    return div.innerHTML;
}


// ============================================================
// FORMAT ANSWER
// ============================================================

function formatAnswer(text) {

    if (!text) {
        return "";
    }

    let safeText =
        escapeHtml(text);

    // Markdown bold
    safeText =
        safeText.replace(
            /\*\*(.*?)\*\*/g,
            "<strong>$1</strong>"
        );

    // Normalize Unicode citations
    safeText =
        safeText.replace(
            /【([^】]+)】/g,
            "[$1]"
        );

    // Line breaks
    safeText =
        safeText.replace(
            /\n/g,
            "<br>"
        );

    return safeText;
}


// ============================================================
// EXTRACT CITATIONS
// ============================================================

function getCitedSourceKeys(answer) {

    const citedKeys =
        new Set();

    if (!answer) {
        return citedKeys;
    }

    const normalizedAnswer =
        answer.replace(
            /【([^】]+)】/g,
            "[$1]"
        );

    const citationPattern =
        /\[([^\],]+?)(?:,\s*Page\s*(\d+))?\]/gi;

    let match;

    while (
        (match =
            citationPattern.exec(
                normalizedAnswer
            )) !== null
    ) {

        const filename =
            match[1].trim();

        const page =
            match[2]
                ? Number(match[2])
                : null;

        citedKeys.add(
            `${filename}|${page}`
        );
    }

    return citedKeys;
}


// ============================================================
// FILTER SOURCES USED IN ANSWER
// ============================================================

function filterUsedSources(
    answer,
    sources
) {

    const uniqueSources =
        getUniqueSources(sources);

    if (uniqueSources.length === 0) {
        return [];
    }

    const citedKeys =
        getCitedSourceKeys(answer);

    if (citedKeys.size > 0) {

        const used =
            uniqueSources.filter(
                source => {

                    const key =
                        `${source.filename}|${source.page_number}`;

                    return citedKeys.has(key);
                }
            );

        if (used.length > 0) {
            return used;
        }
    }

    // Fallback:
    // never show all retrieved sources.
    return [
        uniqueSources[0]
    ];
}


// ============================================================
// CREATE CHAT SECTION
// ============================================================

function createChatSection(title) {

    const section =
        document.createElement("div");

    section.className =
        "chat-sources";

    const heading =
        document.createElement("strong");

    heading.textContent =
        title;

    section.appendChild(
        heading
    );

    return section;
}


// ============================================================
// RENDER AGENT ANSWER
// ============================================================

function renderAgentAnswer(data) {

    const messages =
        $("chatMessages");

    if (!messages) {
        return;
    }

    const wrapper =
        document.createElement("div");

    wrapper.className =
        "chat-message assistant-message";

    // --------------------------------------------------------
    // LABEL
    // --------------------------------------------------------

    const label =
        document.createElement("div");

    label.className =
        "chat-message-label";

    label.textContent =
        "EnterpriseIQ";

    wrapper.appendChild(label);

    // --------------------------------------------------------
    // MAIN ASSISTANT BUBBLE
    // --------------------------------------------------------

    const bubble =
        document.createElement("div");

    bubble.className =
        "chat-bubble assistant";

    // --------------------------------------------------------
    // FINAL ANSWER
    // --------------------------------------------------------

    const answer =
        document.createElement("div");

    answer.className =
        "assistant-answer";

    answer.innerHTML =
        formatAnswer(
            data.answer ||
            "I could not generate an answer."
        );

    bubble.appendChild(
        answer
    );

    // --------------------------------------------------------
    // TOOLS USED
    // --------------------------------------------------------

    const tools =
        Array.isArray(data.tools)
            ? data.tools
            : [];

    if (tools.length > 0) {

        const section =
            createChatSection(
                "Tools Used"
            );

        const toolsRow =
            document.createElement("div");

        toolsRow.className =
            "tools-used";

        toolsRow.textContent =
            formatTools(tools);

        section.appendChild(
            toolsRow
        );

        bubble.appendChild(
            section
        );
    }

    // --------------------------------------------------------
    // SOURCES
    // --------------------------------------------------------

    const sources =
        filterUsedSources(
            data.answer || "",
            data.sources
        );

    if (sources.length > 0) {

        const section =
            createChatSection(
                "Sources"
            );

        sources.forEach(
            source => {

                const item =
                    document.createElement("div");

                item.className =
                    "source-item";

                const icon =
                    document.createElement("span");

                icon.className =
                    "source-icon";

                icon.textContent =
                    "📄";

                const sourceText =
                    document.createElement("span");

                sourceText.className =
                    "source-text";

                const filename =
                    document.createElement("span");

                filename.className =
                    "source-filename";

                filename.textContent =
                    source.filename;

                sourceText.appendChild(
                    filename
                );

                if (
                    source.page_number !== null
                ) {

                    const page =
                        document.createElement("span");

                    page.className =
                        "source-page";

                    page.textContent =
                        `Page ${source.page_number}`;

                    sourceText.appendChild(
                        page
                    );
                }

                item.appendChild(icon);
                item.appendChild(sourceText);

                section.appendChild(item);
            }
        );

        bubble.appendChild(section);
    }

    // --------------------------------------------------------
    // APPEND MESSAGE
    // --------------------------------------------------------

    wrapper.appendChild(bubble);

    messages.appendChild(wrapper);

    messages.scrollTop =
        messages.scrollHeight;
}


// ============================================================
// SEND CHAT
// ============================================================

async function sendChat() {

    const input =
        $("chatInput");

    const sendButton =
        $("sendButton");

    if (!input) {
        return;
    }

    const question =
        input.value.trim();

    if (!question) {
        return;
    }

    addUserMessage(question);

    input.value = "";

    if (sendButton) {

        sendButton.disabled = true;

        sendButton.textContent =
            "Thinking...";
    }

    addLoadingMessage();

    try {

        const data =
            await apiRequest(
                "/api/agent",
                {
                    method: "POST",

                    body: JSON.stringify({
                        question,
                        top_k: 5
                    })
                }
            );

        removeLoadingMessage();

        if (
            data.error &&
            !data.answer
        ) {

            addErrorMessage(
                data.error
            );

            return;
        }

        renderAgentAnswer(data);

    } catch (error) {

        console.error(
            "Agent request failed:",
            error
        );

        removeLoadingMessage();

        addErrorMessage(
            `Unable to process your request: ${error.message}`
        );

    } finally {

        if (sendButton) {

            sendButton.disabled =
                false;

            sendButton.textContent =
                "Send";
        }

        input.focus();
    }
}


// ============================================================
// DOCUMENTS
// ============================================================

async function loadDocuments() {

    const table =
        $("documentsTable");

    try {

        const data =
            await apiRequest(
                "/api/documents"
            );

        let documents = [];

        if (Array.isArray(data)) {

            documents =
                data;

        } else if (
            data &&
            Array.isArray(data.documents)
        ) {

            documents =
                data.documents;
        }

        renderDocuments(documents);

    } catch (error) {

        console.error(
            "Document loading failed:",
            error
        );

        if (table) {

            table.innerHTML = `
                <div class="loading">
                    Unable to load documents.
                </div>
            `;
        }
    }
}


// ============================================================
// RENDER DOCUMENTS
// ============================================================

function renderDocuments(documents) {

    const table =
        $("documentsTable");

    const count =
        $("documentCount");

    if (count) {
        count.textContent =
            documents.length;
    }

    if (!table) {
        return;
    }

    if (documents.length === 0) {

        table.innerHTML = `
            <div class="loading">
                No documents available.
            </div>
        `;

        return;
    }

    let html = `
        <table class="data-table">

            <thead>

                <tr>

                    <th>File</th>

                    <th>Type</th>

                    <th>Status</th>

                    <th>Access</th>

                    <th>Uploaded By</th>

                </tr>

            </thead>

            <tbody>
    `;

    documents.forEach(
        document => {

            html += `
                <tr>

                    <td>
                        ${escapeHtml(
                            document.original_filename ||
                            document.filename ||
                            "-"
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            document.file_type ||
                            "-"
                        )}
                    </td>

                    <td>

                        <span class="status-badge">
                            ${escapeHtml(
                                document.status ||
                                "-"
                            )}
                        </span>

                    </td>

                    <td>
                        ${escapeHtml(
                            document.access_scope ||
                            "-"
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            String(
                                document.uploaded_by ??
                                "-"
                            )
                        )}
                    </td>

                </tr>
            `;
        }
    );

    html += `
            </tbody>

        </table>
    `;

    table.innerHTML =
        html;
}


// ============================================================
// UPLOAD DOCUMENT
// ============================================================

async function uploadDocument() {

    const fileInput =
        $("documentFile");

    const message =
        $("uploadMessage");

    if (
        !fileInput ||
        !fileInput.files ||
        fileInput.files.length === 0
    ) {

        if (message) {

            message.textContent =
                "Please select a file.";

            message.style.color =
                "#c0392b";
        }

        return;
    }

    const file =
        fileInput.files[0];

    const formData =
        new FormData();

    formData.append(
        "file",
        file
    );

    try {

        if (message) {

            message.textContent =
                "Uploading document...";

            message.style.color =
                "#667085";
        }

        await apiRequest(
            "/api/documents/upload",
            {
                method: "POST",
                body: formData
            }
        );

        if (message) {

            message.textContent =
                "Document uploaded successfully.";

            message.style.color =
                "#18794e";
        }

        fileInput.value = "";

        await loadDocuments();

    } catch (error) {

        console.error(
            "Document upload failed:",
            error
        );

        if (message) {

            message.textContent =
                error.message;

            message.style.color =
                "#c0392b";
        }
    }
}


// ============================================================
// EVALUATION
// ============================================================

function loadEvaluationDashboard() {

    // Evaluation values are from the
    // completed backend evaluation run.

    return;
}


// ============================================================
// ADMIN USERS
// ============================================================

async function loadUsers() {

    if (
        !currentUser ||
        currentUser.role !== "admin"
    ) {
        return;
    }

    const table =
        $("usersTable");

    if (!table) {
        return;
    }

    try {

        const data =
            await apiRequest(
                "/api/users"
            );

        const users =
            Array.isArray(data)
                ? data
                : [];

        renderUsers(users);

    } catch (error) {

        console.error(
            "User loading failed:",
            error
        );

        table.innerHTML = `
            <div class="loading">
                Unable to load users.
            </div>
        `;
    }
}


// ============================================================
// RENDER USERS
// ============================================================

function renderUsers(users) {

    const table =
        $("usersTable");

    if (!table) {
        return;
    }

    if (users.length === 0) {

        table.innerHTML = `
            <div class="loading">
                No users found.
            </div>
        `;

        return;
    }

    let html = `
        <table class="data-table">

            <thead>

                <tr>

                    <th>Name</th>

                    <th>Email</th>

                    <th>Role</th>

                    <th>Status</th>

                </tr>

            </thead>

            <tbody>
    `;

    users.forEach(
        user => {

            html += `
                <tr>

                    <td>
                        ${escapeHtml(
                            user.full_name ||
                            "-"
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            user.email ||
                            "-"
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            user.role ||
                            "-"
                        )}
                    </td>

                    <td>
                        ${
                            user.is_active
                                ? "Active"
                                : "Inactive"
                        }
                    </td>

                </tr>
            `;
        }
    );

    html += `
            </tbody>

        </table>
    `;

    table.innerHTML =
        html;
}


// ============================================================
// KEYBOARD SHORTCUT
// ============================================================

document.addEventListener(
    "keydown",
    event => {

        const input =
            $("chatInput");

        if (!input) {
            return;
        }

        if (
            document.activeElement === input &&
            event.key === "Enter" &&
            !event.shiftKey
        ) {

            event.preventDefault();

            sendChat();
        }
    }
);


// ============================================================
// INITIALIZATION
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    () => {

        loadCurrentUser();
    }
);