// ============================================================
// ENTERPRISEIQ - COMPLETE FRONTEND APP.JS
// ============================================================

const API_BASE_URL = "http://127.0.0.1:8000";

const TOKEN_KEY = "enterpriseiq_token";
const USER_KEY = "enterpriseiq_user";

let currentUser = null;


// ============================================================
// INITIALIZATION
// ============================================================

document.addEventListener("DOMContentLoaded", async () => {

    const token = localStorage.getItem(TOKEN_KEY);

    if (token) {

        try {

            const user = await apiRequest(
                "/api/auth/me"
            );

            currentUser = user;

            localStorage.setItem(
                USER_KEY,
                JSON.stringify(user)
            );

            showApplication();

        } catch (error) {

            console.error(
                "Session validation failed:",
                error
            );

            logout();

        }

    } else {

        showLogin();

    }

    checkBackendStatus();

    const chatInput =
        document.getElementById("chatInput");

    if (chatInput) {

        chatInput.addEventListener(
            "keydown",
            function (event) {

                if (
                    event.key === "Enter" &&
                    !event.shiftKey
                ) {

                    event.preventDefault();

                    sendChat();

                }

            }
        );

    }

});


// ============================================================
// API REQUEST
// ============================================================

async function apiRequest(
    endpoint,
    options = {}
) {

    const headers = {
        ...(options.headers || {})
    };

    const token =
        localStorage.getItem(TOKEN_KEY);

    if (token) {

        headers.Authorization =
            `Bearer ${token}`;

    }

    if (
        options.body &&
        !(options.body instanceof FormData)
    ) {

        headers["Content-Type"] =
            "application/json";

    }

    let response;

    try {

        response = await fetch(
            `${API_BASE_URL}${endpoint}`,
            {
                ...options,
                headers
            }
        );

    } catch (error) {

        throw new Error(
            "Unable to connect to backend."
        );

    }

    let data = null;

    try {

        data = await response.json();

    } catch (error) {

        data = null;

    }

    if (!response.ok) {

        let message =
            data?.detail ||
            data?.message ||
            `Request failed with status ${response.status}`;

        if (Array.isArray(message)) {

            message =
                message
                    .map(item =>
                        item.msg || String(item)
                    )
                    .join(", ");

        }

        throw new Error(message);

    }

    return data;

}


// ============================================================
// AUTH - SHOW LOGIN
// ============================================================

function showLogin() {

    const loginForm =
        document.getElementById("loginForm");

    const registerForm =
        document.getElementById("registerForm");

    if (loginForm) {

        loginForm.classList.remove("hidden");

    }

    if (registerForm) {

        registerForm.classList.add("hidden");

    }

}


// ============================================================
// AUTH - SHOW REGISTER
// ============================================================

function showRegister() {

    const loginForm =
        document.getElementById("loginForm");

    const registerForm =
        document.getElementById("registerForm");

    if (loginForm) {

        loginForm.classList.add("hidden");

    }

    if (registerForm) {

        registerForm.classList.remove("hidden");

    }

}


// ============================================================
// LOGIN
// ============================================================

async function login() {

    const email =
        document
            .getElementById("loginEmail")
            .value
            .trim();

    const password =
        document
            .getElementById("loginPassword")
            .value;

    const message =
        document.getElementById(
            "loginMessage"
        );

    const button =
        document.getElementById(
            "loginButton"
        );

    if (!email || !password) {

        if (message) {

            message.textContent =
                "Please enter email and password.";

        }

        return;

    }

    try {

        if (button) {

            button.disabled = true;
            button.textContent = "Logging in...";

        }

        if (message) {

            message.textContent = "";

        }

        const data =
            await apiRequest(
                "/api/auth/login",
                {
                    method: "POST",
                    body: JSON.stringify({
                        email,
                        password
                    })
                }
            );

        const token =
            data.access_token ||
            data.token;

        if (!token) {

            throw new Error(
                "Login successful but token was not returned."
            );

        }

        localStorage.setItem(
            TOKEN_KEY,
            token
        );

        const user =
            data.user ||
            await apiRequest(
                "/api/auth/me"
            );

        currentUser = user;

        localStorage.setItem(
            USER_KEY,
            JSON.stringify(user)
        );

        showApplication();

    } catch (error) {

        console.error(
            "Login error:",
            error
        );

        if (message) {

            message.textContent =
                error.message;

        }

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

    const fullName =
        document
            .getElementById("registerName")
            .value
            .trim();

    const email =
        document
            .getElementById("registerEmail")
            .value
            .trim();

    const password =
        document
            .getElementById("registerPassword")
            .value;

    const message =
        document.getElementById(
            "registerMessage"
        );

    const button =
        document.getElementById(
            "registerButton"
        );

    if (!fullName || !email || !password) {

        if (message) {

            message.textContent =
                "Please fill all fields.";

        }

        return;

    }

    if (password.length < 8) {

        if (message) {

            message.textContent =
                "Password must contain at least 8 characters.";

        }

        return;

    }

    try {

        if (button) {

            button.disabled = true;
            button.textContent =
                "Creating Account...";

        }

        if (message) {

            message.textContent = "";

        }

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

        if (message) {

            message.textContent =
                "Account created successfully. Please login.";

        }

        const loginEmail =
            document.getElementById(
                "loginEmail"
            );

        if (loginEmail) {

            loginEmail.value =
                email;

        }

        document
            .getElementById("registerName")
            .value = "";

        document
            .getElementById("registerEmail")
            .value = "";

        document
            .getElementById("registerPassword")
            .value = "";

        setTimeout(
            () => {
                showLogin();
            },
            1000
        );

    } catch (error) {

        console.error(
            "Registration error:",
            error
        );

        if (message) {

            message.textContent =
                error.message;

        }

    } finally {

        if (button) {

            button.disabled = false;
            button.textContent =
                "Create Account";

        }

    }

}


// ============================================================
// SHOW APPLICATION
// ============================================================

function showApplication() {

    const authScreen =
        document.getElementById(
            "authScreen"
        );

    const appScreen =
        document.getElementById(
            "appScreen"
        );

    if (authScreen) {

        authScreen.classList.add("hidden");

    }

    if (appScreen) {

        appScreen.classList.remove("hidden");

    }

    updateUserUI();

    showPage("dashboard");

    loadDocuments();

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
        currentUser.name ||
        currentUser.email ||
        "User";

    const role =
        currentUser.role ||
        "user";

    const sidebarName =
        document.getElementById(
            "sidebarUserName"
        );

    const sidebarRole =
        document.getElementById(
            "sidebarUserRole"
        );

    const topName =
        document.getElementById(
            "topUserName"
        );

    const welcomeName =
        document.getElementById(
            "welcomeUser"
        );

    const avatar =
        document.getElementById(
            "userAvatar"
        );

    const adminNav =
        document.getElementById(
            "adminNav"
        );

    if (sidebarName) {

        sidebarName.textContent =
            name;

    }

    if (sidebarRole) {

        sidebarRole.textContent =
            role;

    }

    if (topName) {

        topName.textContent =
            name;

    }

    if (welcomeName) {

        welcomeName.textContent =
            name;

    }

    if (avatar) {

        avatar.textContent =
            name
                .charAt(0)
                .toUpperCase();

    }

    if (adminNav) {

        if (role === "admin") {

            adminNav.classList.remove(
                "hidden"
            );

        } else {

            adminNav.classList.add(
                "hidden"
            );

        }

    }

}


// ============================================================
// LOGOUT
// ============================================================

function logout() {

    localStorage.removeItem(
        TOKEN_KEY
    );

    localStorage.removeItem(
        USER_KEY
    );

    currentUser = null;

    const appScreen =
        document.getElementById(
            "appScreen"
        );

    const authScreen =
        document.getElementById(
            "authScreen"
        );

    if (appScreen) {

        appScreen.classList.add("hidden");

    }

    if (authScreen) {

        authScreen.classList.remove("hidden");

    }

    showLogin();

}


// ============================================================
// PAGE NAVIGATION
// ============================================================

function showPage(pageName) {

    const pages =
        document.querySelectorAll(
            ".page"
        );

    pages.forEach(
        page => {

            page.classList.remove(
                "active-page"
            );

        }
    );

    const targetPage =
        document.getElementById(
            `${pageName}Page`
        );

    if (!targetPage) {

        return;

    }

    targetPage.classList.add(
        "active-page"
    );

    const navButtons =
        document.querySelectorAll(
            ".sidebar-nav button[data-page]"
        );

    navButtons.forEach(
        button => {

            button.classList.remove(
                "active"
            );

            if (
                button.dataset.page ===
                pageName
            ) {

                button.classList.add(
                    "active"
                );

            }

        }
    );

    const pageTitle =
        document.getElementById(
            "pageTitle"
        );

    const pageSubtitle =
        document.getElementById(
            "pageSubtitle"
        );

    const titles = {

        dashboard: [
            "Dashboard",
            "Enterprise intelligence at your fingertips."
        ],

        chat: [
            "Chat",
            "Ask questions across enterprise knowledge."
        ],

        documents: [
            "Documents",
            "Upload and manage enterprise documents."
        ],

        evaluations: [
            "Evaluations",
            "Measure EnterpriseIQ performance."
        ],

        admin: [
            "Admin",
            "Manage EnterpriseIQ users."
        ]

    };

    if (titles[pageName]) {

        if (pageTitle) {

            pageTitle.textContent =
                titles[pageName][0];

        }

        if (pageSubtitle) {

            pageSubtitle.textContent =
                titles[pageName][1];

        }

    }

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
// BACKEND STATUS
// ============================================================

async function checkBackendStatus() {

    const status =
        document.getElementById(
            "backendStatus"
        );

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

        if (status) {

            status.innerHTML =
                '<span class="status-dot"></span> Backend connected';

        }

    } catch (error) {

        if (status) {

            status.innerHTML =
                '<span class="status-dot"></span> Backend unavailable';

        }

    }

}


// ============================================================
// CHAT - EXAMPLE
// ============================================================

function useExample(question) {

    const input =
        document.getElementById(
            "chatInput"
        );

    if (input) {

        input.value =
            question;

        input.focus();

    }

}


// ============================================================
// CHAT - SEND
// ============================================================

async function sendChat() {

    const input =
        document.getElementById(
            "chatInput"
        );

    const button =
        document.getElementById(
            "sendButton"
        );

    const messages =
        document.getElementById(
            "chatMessages"
        );

    if (!input || !messages) {

        return;

    }

    const question =
        input.value.trim();

    if (!question) {

        return;

    }

    const empty =
        document.getElementById(
            "chatEmpty"
        );

    if (empty) {

        empty.remove();

    }

    appendUserMessage(
        messages,
        question
    );

    input.value = "";

    if (button) {

        button.disabled = true;
        button.textContent = "Thinking...";

    }

    const loading =
        appendLoadingMessage(
            messages
        );

    try {

        const data =
            await apiRequest(
                "/api/agent",
                {
                    method: "POST",
                    body: JSON.stringify({
                        question
                    })
                }
            );

        if (loading) {

            loading.remove();

        }

        renderAgentResponse(
            messages,
            data
        );

    } catch (error) {

        if (loading) {

            loading.remove();

        }

        appendErrorMessage(
            messages,
            error.message
        );

    } finally {

        if (button) {

            button.disabled = false;
            button.textContent = "Send";

        }

    }

}


// ============================================================
// CHAT - USER MESSAGE
// ============================================================

function appendUserMessage(
    container,
    text
) {

    const wrapper =
        document.createElement(
            "div"
        );

    wrapper.className =
        "chat-message user-message";

    wrapper.innerHTML =
        `<div class="message-content">${escapeHtml(text)}</div>`;

    container.appendChild(
        wrapper
    );

    container.scrollTop =
        container.scrollHeight;

}


// ============================================================
// CHAT - LOADING
// ============================================================

function appendLoadingMessage(
    container
) {

    const wrapper =
        document.createElement(
            "div"
        );

    wrapper.className =
        "chat-message assistant-message";

    wrapper.innerHTML =
        `<div class="message-content">Thinking...</div>`;

    container.appendChild(
        wrapper
    );

    container.scrollTop =
        container.scrollHeight;

    return wrapper;

}


// ============================================================
// CHAT - ERROR
// ============================================================

function appendErrorMessage(
    container,
    message
) {

    const wrapper =
        document.createElement(
            "div"
        );

    wrapper.className =
        "chat-message assistant-message";

    wrapper.innerHTML =
        `<div class="message-content">Error: ${escapeHtml(message)}</div>`;

    container.appendChild(
        wrapper
    );

    container.scrollTop =
        container.scrollHeight;

}


// ============================================================
// CHAT - AGENT RESPONSE
// ============================================================

function renderAgentResponse(
    container,
    data
) {

    const wrapper =
        document.createElement(
            "div"
        );

    wrapper.className =
        "chat-message assistant-message";

    const answer =
        data.answer ||
        data.final_answer ||
        data.message ||
        "No answer returned.";

    const tools =
        data.tools ||
        data.tool_names ||
        data.selected_tools ||
        [];

    const sources =
        data.sources ||
        [];

    let html =
        `<div class="message-content">`;

    html +=
        `<div>${formatAnswer(answer)}</div>`;

    if (
        Array.isArray(tools) &&
        tools.length
    ) {

        html += `
            <div style="
                margin-top:12px;
                font-size:11px;
                color:#667085;
            ">
                <strong>Tools used:</strong>
                ${tools
                    .map(tool =>
                        `<span style="
                            display:inline-block;
                            margin-left:5px;
                            padding:3px 7px;
                            border-radius:5px;
                            background:#f2f4f7;
                        ">${escapeHtml(tool)}</span>`
                    )
                    .join("")
                }
            </div>
        `;

    }

    if (
        Array.isArray(sources) &&
        sources.length
    ) {

        html += `
            <div style="
                margin-top:12px;
                font-size:11px;
                color:#667085;
            ">
                <strong>Sources:</strong>
        `;

        const uniqueSources =
            [];

        sources.forEach(
            source => {

                const filename =
                    source.filename ||
                    source.document ||
                    "Unknown document";

                const page =
                    source.page_number;

                const label =
                    page
                        ? `${filename}, Page ${page}`
                        : filename;

                if (
                    !uniqueSources.includes(
                        label
                    )
                ) {

                    uniqueSources.push(
                        label
                    );

                }

            }
        );

        html +=
            uniqueSources
                .map(
                    source =>
                        `<div style="margin-top:4px;">• ${escapeHtml(source)}</div>`
                )
                .join("");

        html += "</div>";

    }

    html += "</div>";

    wrapper.innerHTML =
        html;

    container.appendChild(
        wrapper
    );

    container.scrollTop =
        container.scrollHeight;

}


// ============================================================
// FORMAT ANSWER
// ============================================================

function formatAnswer(
    answer
) {

    if (!answer) {

        return "";

    }

    return escapeHtml(
        String(answer)
    )
        .replace(
            /\n/g,
            "<br>"
        );

}


// ============================================================
// DOCUMENT UPLOAD
// ============================================================

async function uploadDocument() {

    const fileInput =
        document.getElementById(
            "documentFile"
        );

    const button =
        document.getElementById(
            "uploadButton"
        );

    const message =
        document.getElementById(
            "uploadMessage"
        );

    if (
        !fileInput ||
        !fileInput.files.length
    ) {

        if (message) {

            message.textContent =
                "Please select a document.";

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

        if (button) {

            button.disabled = true;
            button.textContent =
                "Uploading...";

        }

        if (message) {

            message.textContent =
                "Uploading document...";

        }

        const data =
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

        }

        console.log(
            "Document uploaded:",
            data
        );

        fileInput.value = "";

        await loadDocuments();

    } catch (error) {

        console.error(
            "Upload error:",
            error
        );

        if (message) {

            message.textContent =
                error.message;

        }

    } finally {

        if (button) {

            button.disabled = false;
            button.textContent =
                "Upload Document";

        }

    }

}


// ============================================================
// LOAD DOCUMENTS
// ============================================================

async function loadDocuments() {

    const container =
        document.getElementById(
            "documentsTable"
        );

    if (!container) {

        return;

    }

    try {

        container.innerHTML =
            '<div class="loading">Loading documents...</div>';

        const data =
            await apiRequest(
                "/api/documents"
            );

        /*
         * Backend response:
         *
         * {
         *     "total": 2,
         *     "documents": [...]
         * }
         */

        const documents =
            Array.isArray(data)
                ? data
                : (
                    Array.isArray(
                        data.documents
                    )
                        ? data.documents
                        : []
                );

        const total =
            typeof data.total === "number"
                ? data.total
                : documents.length;

        renderDocuments(
            documents
        );

        updateDocumentCounts(
            total
        );

    } catch (error) {

        console.error(
            "Document loading error:",
            error
        );

        container.innerHTML = `
            <div class="loading">
                ${escapeHtml(error.message)}
            </div>
        `;

        updateDocumentCounts(0);

    }

}


// ============================================================
// DOCUMENT COUNTS
// ============================================================

function updateDocumentCounts(
    count
) {

    /*
     * New preferred dashboard ID.
     */

    const dashboardCount =
        document.getElementById(
            "dashboardDocumentCount"
        );

    /*
     * Existing/alternate dashboard ID.
     */

    const oldDashboardCount =
        document.getElementById(
            "documentCount"
        );

    /*
     * Documents page count.
     */

    const listCount =
        document.getElementById(
            "documentListCount"
        );

    if (dashboardCount) {

        dashboardCount.textContent =
            count;

    }

    /*
     * Backward compatibility with
     * the current index.html.
     */

    if (
        oldDashboardCount &&
        oldDashboardCount !== dashboardCount
    ) {

        oldDashboardCount.textContent =
            count;

    }

    if (listCount) {

        listCount.textContent =
            count;

    }

}


// ============================================================
// FORMAT FILE SIZE
// ============================================================

function formatFileSize(
    bytes
) {

    if (
        bytes === null ||
        bytes === undefined ||
        Number.isNaN(Number(bytes))
    ) {

        return "-";

    }

    const size =
        Number(bytes);

    if (size < 1024) {

        return `${size} B`;

    }

    if (size < 1024 * 1024) {

        return `${(
            size / 1024
        ).toFixed(1)} KB`;

    }

    return `${(
        size / (
            1024 * 1024
        )
    ).toFixed(1)} MB`;

}


// ============================================================
// FORMAT DOCUMENT STATUS
// ============================================================

function formatDocumentStatus(
    status
) {

    if (!status) {

        return "-";

    }

    const value =
        String(status);

    return value
        .charAt(0)
        .toUpperCase() +
        value.slice(1);

}


// ============================================================
// RENDER DOCUMENTS
// ============================================================

function renderDocuments(
    documents
) {

    const container =
        document.getElementById(
            "documentsTable"
        );

    if (!container) {

        return;

    }

    if (!documents.length) {

        container.innerHTML = `
            <div class="loading">
                No documents found.
            </div>
        `;

        return;

    }

    let html = `
        <div style="overflow-x:auto;">
            <table style="
                width:100%;
                border-collapse:collapse;
                font-size:12px;
            ">

                <thead>

                    <tr>

                        <th style="text-align:left;padding:10px;">
                            Document
                        </th>

                        <th style="text-align:left;padding:10px;">
                            Type
                        </th>

                        <th style="text-align:left;padding:10px;">
                            Size
                        </th>

                        <th style="text-align:left;padding:10px;">
                            Status
                        </th>

                        <th style="text-align:left;padding:10px;">
                            Access
                        </th>

                        <th style="text-align:left;padding:10px;">
                            Chunks
                        </th>

                    </tr>

                </thead>

                <tbody>
    `;

    documents.forEach(
        document => {

            const filename =
                document.original_filename ||
                document.filename ||
                document.file_name ||
                document.name ||
                "Unknown";

            const fileType =
                document.file_type ||
                document.content_type ||
                "-";

            const fileSize =
                formatFileSize(
                    document.file_size
                );

            const documentStatus =
                formatDocumentStatus(
                    document.status
                );

            const accessScope =
                document.access_scope ||
                document.scope ||
                "private";

            const chunkCount =
                document.chunk_count ??
                document.total_chunks ??
                0;

            html += `
                <tr style="
                    border-top:1px solid #eaecf0;
                ">

                    <td style="padding:10px;">
                        ${escapeHtml(filename)}
                    </td>

                    <td style="padding:10px;">
                        ${escapeHtml(fileType)}
                    </td>

                    <td style="padding:10px;">
                        ${escapeHtml(fileSize)}
                    </td>

                    <td style="padding:10px;">
                        ${escapeHtml(documentStatus)}
                    </td>

                    <td style="padding:10px;">
                        ${escapeHtml(accessScope)}
                    </td>

                    <td style="padding:10px;">
                        ${escapeHtml(chunkCount)}
                    </td>

                </tr>
            `;

        }
    );

    html += `
                </tbody>

            </table>
        </div>
    `;

    container.innerHTML =
        html;

}


// ============================================================
// EVALUATION MESSAGE
// ============================================================

function setEvaluationMessage(
    message
) {

    const element =
        document.getElementById(
            "evaluationMessage"
        );

    if (element) {

        element.textContent =
            message;

    }

}


// ============================================================
// EVALUATION FORMAT
// ============================================================

function formatEvaluationValue(
    value
) {

    if (
        value === null ||
        value === undefined
    ) {

        return "--";

    }

    const number =
        Number(value);

    if (
        Number.isNaN(number)
    ) {

        return String(value);

    }

    return number.toFixed(4);

}


// ============================================================
// RENDER AGENT EVALUATION
// ============================================================

function renderAgentEvaluation(
    data
) {

    const route =
        document.getElementById(
            "routeAccuracy"
        );

    const selection =
        document.getElementById(
            "toolSelectionAccuracy"
        );

    const execution =
        document.getElementById(
            "toolExecutionAccuracy"
        );

    const finalAnswer =
        document.getElementById(
            "finalAnswerAccuracy"
        );

    if (route) {

        route.textContent =
            formatEvaluationValue(
                data.route_accuracy
            );

    }

    if (selection) {

        selection.textContent =
            formatEvaluationValue(
                data.tool_selection_accuracy
            );

    }

    if (execution) {

        execution.textContent =
            formatEvaluationValue(
                data.tool_execution_accuracy
            );

    }

    if (finalAnswer) {

        finalAnswer.textContent =
            formatEvaluationValue(
                data.final_answer_accuracy
            );

    }

}


// ============================================================
// RUN AGENT EVALUATION
// ============================================================

async function runAgentEvaluation() {

    const button =
        document.getElementById(
            "runAgentButton"
        );

    try {

        setEvaluationMessage(
            "Running agent evaluation..."
        );

        if (button) {

            button.disabled = true;
            button.textContent =
                "Running...";

        }

        const data =
            await apiRequest(
                "/api/evaluation/agent",
                {
                    method: "POST",
                    body: JSON.stringify({
                        top_k: 3
                    })
                }
            );

        renderAgentEvaluation(
            data
        );

        setEvaluationMessage(
            `Agent evaluation completed successfully. ${data.total_questions || 0} questions evaluated.`
        );

    } catch (error) {

        console.error(
            "Agent evaluation error:",
            error
        );

        setEvaluationMessage(
            error.message
        );

    } finally {

        if (button) {

            button.disabled = false;
            button.textContent =
                "Run Agent Evaluation";

        }

    }

}


// ============================================================
// RENDER RETRIEVAL EVALUATION
// ============================================================

function renderRetrievalEvaluation(
    data
) {

    const precision =
        document.getElementById(
            "precisionAt3"
        );

    const recall =
        document.getElementById(
            "recallAt3"
        );

    const hitRate =
        document.getElementById(
            "hitRateAt3"
        );

    const mrr =
        document.getElementById(
            "mrr"
        );

    if (precision) {

        precision.textContent =
            formatEvaluationValue(
                data.precision_at_3 ??
                data.precision
            );

    }

    if (recall) {

        recall.textContent =
            formatEvaluationValue(
                data.recall_at_3 ??
                data.recall
            );

    }

    if (hitRate) {

        hitRate.textContent =
            formatEvaluationValue(
                data.hit_rate_at_3 ??
                data.hit_rate
            );

    }

    if (mrr) {

        mrr.textContent =
            formatEvaluationValue(
                data.mrr
            );

    }

}


// ============================================================
// RUN RETRIEVAL EVALUATION
// ============================================================

async function runRetrievalEvaluation() {

    const button =
        document.getElementById(
            "runRetrievalButton"
        );

    try {

        setEvaluationMessage(
            "Running retrieval evaluation..."
        );

        if (button) {

            button.disabled = true;
            button.textContent =
                "Running...";

        }

        const data =
            await apiRequest(
                "/api/evaluation/retrieval",
                {
                    method: "POST",
                    body: JSON.stringify({
                        top_k: 3
                    })
                }
            );

        renderRetrievalEvaluation(
            data
        );

        setEvaluationMessage(
            "Retrieval evaluation completed successfully."
        );

    } catch (error) {

        console.error(
            "Retrieval evaluation error:",
            error
        );

        setEvaluationMessage(
            error.message
        );

    } finally {

        if (button) {

            button.disabled = false;
            button.textContent =
                "Run Retrieval Evaluation";

        }

    }

}


// ============================================================
// RENDER GENERATION EVALUATION
// ============================================================

function renderGenerationEvaluation(
    data
) {

    const faithfulness =
        document.getElementById(
            "faithfulness"
        );

    const relevance =
        document.getElementById(
            "answerRelevance"
        );

    const correctness =
        document.getElementById(
            "answerCorrectness"
        );

    if (faithfulness) {

        faithfulness.textContent =
            formatEvaluationValue(
                data.faithfulness
            );

    }

    if (relevance) {

        relevance.textContent =
            formatEvaluationValue(
                data.answer_relevance ??
                data.answerRelevance
            );

    }

    if (correctness) {

        correctness.textContent =
            formatEvaluationValue(
                data.answer_correctness ??
                data.answerCorrectness
            );

    }

}


// ============================================================
// RUN GENERATION EVALUATION
// ============================================================

async function runGenerationEvaluation() {

    const button =
        document.getElementById(
            "runGenerationButton"
        );

    try {

        setEvaluationMessage(
            "Running generation evaluation..."
        );

        if (button) {

            button.disabled = true;
            button.textContent =
                "Running...";

        }

        const data =
            await apiRequest(
                "/api/evaluation/generation",
                {
                    method: "POST",
                    body: JSON.stringify({
                        top_k: 3
                    })
                }
            );

        renderGenerationEvaluation(
            data
        );

        setEvaluationMessage(
            "Generation evaluation completed successfully."
        );

    } catch (error) {

        console.error(
            "Generation evaluation error:",
            error
        );

        setEvaluationMessage(
            error.message
        );

    } finally {

        if (button) {

            button.disabled = false;
            button.textContent =
                "Run Generation Evaluation";

        }

    }

}


// ============================================================
// EVALUATION DASHBOARD
// ============================================================

async function loadEvaluationDashboard() {

    setEvaluationMessage(
        "Evaluation dashboard ready. Run an evaluation to refresh metrics."
    );

}


// ============================================================
// ADMIN - LOAD USERS
// ============================================================

async function loadUsers() {

    const container =
        document.getElementById(
            "usersTable"
        );

    if (!container) {

        return;

    }

    try {

        container.innerHTML =
            '<div class="loading">Loading users...</div>';

        const data =
            await apiRequest(
                "/api/users"
            );

        const users =
            Array.isArray(data)
                ? data
                : (
                    data.users ||
                    data.items ||
                    []
                );

        renderUsers(
            users
        );

    } catch (error) {

        console.error(
            "Users loading error:",
            error
        );

        container.innerHTML =
            `<div class="loading">${escapeHtml(error.message)}</div>`;

    }

}


// ============================================================
// ADMIN - RENDER USERS
// ============================================================

function renderUsers(
    users
) {

    const container =
        document.getElementById(
            "usersTable"
        );

    if (!container) {

        return;

    }

    if (!users.length) {

        container.innerHTML =
            '<div class="loading">No users found.</div>';

        return;

    }

    let html = `
        <div style="overflow-x:auto;">
            <table style="
                width:100%;
                border-collapse:collapse;
                font-size:12px;
            ">

                <thead>

                    <tr>

                        <th style="text-align:left;padding:10px;">
                            Name
                        </th>

                        <th style="text-align:left;padding:10px;">
                            Email
                        </th>

                        <th style="text-align:left;padding:10px;">
                            Role
                        </th>

                        <th style="text-align:left;padding:10px;">
                            Status
                        </th>

                    </tr>

                </thead>

                <tbody>
    `;

    users.forEach(
        user => {

            const name =
                user.full_name ||
                user.name ||
                "-";

            const email =
                user.email ||
                "-";

            const role =
                user.role ||
                "user";

            const active =
                user.is_active ??
                user.active;

            html += `
                <tr style="border-top:1px solid #eaecf0;">

                    <td style="padding:10px;">
                        ${escapeHtml(name)}
                    </td>

                    <td style="padding:10px;">
                        ${escapeHtml(email)}
                    </td>

                    <td style="padding:10px;">
                        ${escapeHtml(role)}
                    </td>

                    <td style="padding:10px;">
                        ${
                            active === undefined
                                ? "-"
                                : active
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
        </div>
    `;

    container.innerHTML =
        html;

}


// ============================================================
// ESCAPE HTML
// ============================================================

function escapeHtml(
    value
) {

    if (
        value === null ||
        value === undefined
    ) {

        return "";

    }

    return String(value)
        .replace(
            /&/g,
            "&amp;"
        )
        .replace(
            /</g,
            "&lt;"
        )
        .replace(
            />/g,
            "&gt;"
        )
        .replace(
            /"/g,
            "&quot;"
        )
        .replace(
            /'/g,
            "&#039;"
        );

}


// ============================================================
// GLOBAL ERROR LOGGING
// ============================================================

window.addEventListener(
    "error",
    function (event) {

        console.error(
            "Frontend error:",
            event.error || event.message
        );

    }
);


// ============================================================
// DEBUG
// ============================================================

console.log(
    "=========================================="
);

console.log(
    "EnterpriseIQ frontend loaded."
);

console.log(
    "API:",
    API_BASE_URL
);

console.log(
    "=========================================="
);