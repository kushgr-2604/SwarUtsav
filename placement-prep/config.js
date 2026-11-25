(function attachGeminiClient() {
    const DEFAULT_KEY_B64 = "QVEuQWI4Uk42S19USXYwQTFxOUxOZjNzck9YZ1RJdmhEYkdDQnBwclNiRGFYakNwcFJGWEE=";

    async function callDirectGemini(parts, isJson) {
        const apiKey = atob(DEFAULT_KEY_B64);
        const model = "gemini-3.1-flash-lite";
        const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${encodeURIComponent(apiKey)}`;

        const geminiParts = parts.map((p) => {
            if (typeof p.text === "string") return { text: p.text };
            if (p.inlineData) return { inlineData: p.inlineData };
            return {};
        });

        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-goog-api-key": apiKey,
            },
            body: JSON.stringify({
                contents: [{ role: "user", parts: geminiParts }],
                generationConfig: isJson ? { responseMimeType: "application/json" } : {},
            }),
        });

        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            throw new Error(data.error?.message || `Gemini API error (${response.status})`);
        }

        const text =
            (data.candidates?.[0]?.content?.parts || [])
                .map((p) => p.text)
                .filter(Boolean)
                .join("") || data.candidates?.[0]?.content?.parts?.[0]?.text;

        if (!text || !text.trim()) {
            throw new Error("The AI returned no text. Please try again.");
        }

        if (isJson) {
            try {
                let cleaned = text.trim();
                const jsonMatch = cleaned.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
                if (jsonMatch) cleaned = jsonMatch[1].trim();
                const first = cleaned.search(/[{\[]/);
                const last = Math.max(cleaned.lastIndexOf("}"), cleaned.lastIndexOf("]"));
                if (first !== -1 && last !== -1) cleaned = cleaned.slice(first, last + 1);
                return { text, json: JSON.parse(cleaned) };
            } catch {
                throw new Error("AI response did not contain valid JSON.");
            }
        }

        return { text };
    }

    async function callGeminiAPI(input, isJson = false) {
        const parts = typeof input === "string" ? [{ text: input }] : input;

        try {
            const response = await fetch("/api/gemini", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ parts, isJson }),
            });

            if (response.ok) {
                return await response.json();
            }

            const result = await response.json().catch(() => ({}));
            // If endpoint doesn't exist on this host (e.g. static Netlify), use direct fallback
            if (response.status === 404 || response.status === 405) {
                return await callDirectGemini(parts, isJson);
            }

            throw new Error(result.error || `Gemini request failed (${response.status}).`);
        } catch (error) {
            // If failed to fetch backend (network error or static site), fallback to direct API
            if (error.message.includes("Failed to fetch") || error.message.includes("404")) {
                return await callDirectGemini(parts, isJson);
            }
            throw error;
        }
    }

    window.callGeminiAPI = callGeminiAPI;
})();
