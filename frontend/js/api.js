
"use strict";

/**
 * ScholarAI Frontend API Client
 *
 * Phase 4.3
 *
 * Communicates with the FastAPI backend.
 * Real LLM responses will be implemented in Phase 5.
 */

(function () {
    const API_BASE_URL = "http://127.0.0.1:8000";
    const REQUEST_TIMEOUT_MS = 30000;

    /**
     * Send a request to the ScholarAI backend.
     */
    async function request(endpoint, options = {}) {
        const controller = new AbortController();

        const timeoutId = window.setTimeout(() => {
            controller.abort();
        }, REQUEST_TIMEOUT_MS);

        try {
            const response = await fetch(
                `${API_BASE_URL}${endpoint}`,
                {
                    ...options,
                    signal: controller.signal,
                    headers: {
                        Accept: "application/json",
                        ...(options.body
                            ? { "Content-Type": "application/json" }
                            : {}),
                        ...options.headers,
                    },
                }
            );

            const contentType =
                response.headers.get("content-type") || "";

            let data = null;

            if (contentType.includes("application/json")) {
                data = await response.json();
            }

            if (!response.ok) {
                let message = `Request failed (${response.status}).`;

                if (
                    data &&
                    Array.isArray(data.detail) &&
                    data.detail.length > 0
                ) {
                    message = data.detail
                        .map((error) => error.msg || "Invalid request.")
                        .join(" ");
                } else if (
                    data &&
                    typeof data.detail === "string"
                ) {
                    message = data.detail;
                }

                const error = new Error(message);
                error.status = response.status;

                throw error;
            }

            if (!data || typeof data !== "object") {
                throw new Error(
                    "The backend returned an invalid response."
                );
            }

            return data;
        } catch (error) {
            if (error.name === "AbortError") {
                throw new Error(
                    "The request timed out. Please try again."
                );
            }

            if (error instanceof TypeError) {
                throw new Error(
                    "Unable to connect to ScholarAI. " +
                    "Make sure the backend is running at " +
                    "http://127.0.0.1:8000."
                );
            }

            throw error;
        } finally {
            window.clearTimeout(timeoutId);
        }
    }

    /**
     * Send an academic question to the chat API.
     */
    async function sendChatMessage(message, conversationId = null) {
        const trimmedMessage = String(message || "").trim();

        if (!trimmedMessage) {
            throw new Error(
                "Please enter a message before sending."
            );
        }

        if (trimmedMessage.length > 5000) {
            throw new Error(
                "Your message must contain no more than 5000 characters."
            );
        }

        const payload = {
            message: trimmedMessage,
            conversation_id: conversationId || null,
        };

        const data = await request("/api/v1/chat", {
            method: "POST",
            body: JSON.stringify(payload),
        });

        if (
            data.status !== "success" ||
            typeof data.answer !== "string" ||
            !data.answer.trim()
        ) {
            throw new Error(
                "ScholarAI received an unexpected response from the backend."
            );
        }

        return data;
    }

    /**
     * Check backend health.
     */
    async function checkHealth() {
        return request("/health");
    }

    window.ScholarAIAPI = Object.freeze({
        sendChatMessage,
        checkHealth,
    });
})();

