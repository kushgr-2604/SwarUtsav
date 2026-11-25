const FILLERS = /\b(um|uh|like|actually|basically|you know|sort of|kind of)\b/gi;

export type MetricScores = {
  relevance: number;
  completeness: number;
  technical: number;
  keywordCoverage: number;
  grammar: number;
  conciseness: number;
  fillerCount: number;
};

function clamp(n: number) {
  return Math.max(0, Math.min(100, Math.round(n)));
}

export function evaluateAnswer(
  answer: string,
  keywordsCsv: string,
  interviewType: string,
): MetricScores {
  const text = answer.trim();
  const words = text ? text.split(/\s+/).filter(Boolean) : [];
  const lower = text.toLowerCase();
  const keywords = keywordsCsv
    .split(",")
    .map((k) => k.trim())
    .filter(Boolean);
  const hits = keywords.filter((k) => lower.includes(k.toLowerCase())).length;
  const keywordCoverage = keywords.length
    ? (hits / keywords.length) * 100
    : words.length > 20
      ? 72
      : 40;
  const completeness = Math.min(100, (words.length / 90) * 100);
  const fillerCount = (text.match(FILLERS) ?? []).length;
  const grammar = Math.max(45, 92 - fillerCount * 6 - (text.includes("  ") ? 4 : 0));
  const conciseness =
    words.length === 0
      ? 0
      : words.length < 30
        ? 58
        : words.length < 160
          ? 86
          : Math.max(50, 86 - (words.length - 160) / 4);
  const technicalBase =
    interviewType === "HR" || interviewType === "Behavioral" ? 70 : 62;
  const technical = technicalBase + keywordCoverage * 0.28;
  const relevance = 42 + keywordCoverage * 0.45 + Math.min(20, words.length / 6);

  return {
    relevance: clamp(relevance),
    completeness: clamp(completeness),
    technical: clamp(technical),
    keywordCoverage: clamp(keywordCoverage),
    grammar: clamp(grammar),
    conciseness: clamp(conciseness),
    fillerCount,
  };
}

export function aggregateReport(
  metrics: MetricScores[],
  cameraEnabled: boolean,
  avgSpeakingSeconds: number,
) {
  if (!metrics.length) {
    return {
      overall: 0,
      answerQuality: 0,
      communication: 0,
      behavioral: cameraEnabled ? 55 : 40,
      strengths: [] as string[],
      weaknesses: ["No answers were submitted"],
      suggestions: ["Complete a full session with spoken or written answers"],
    };
  }
  const avg = (key: keyof MetricScores) =>
    metrics.reduce((s, m) => s + (typeof m[key] === "number" ? (m[key] as number) : 0), 0) /
    metrics.length;

  const answerQuality = clamp(
    avg("relevance") * 0.25 +
      avg("completeness") * 0.2 +
      avg("technical") * 0.25 +
      avg("keywordCoverage") * 0.15 +
      avg("grammar") * 0.15,
  );
  const fillerAvg = avg("fillerCount");
  const communication = clamp(
    88 - fillerAvg * 8 + Math.min(8, avgSpeakingSeconds / 20) + (avg("conciseness") - 70) / 5,
  );
  const behavioral = clamp(cameraEnabled ? 74 + Math.min(12, avgSpeakingSeconds / 15) : 58);
  const overall = clamp(answerQuality * 0.5 + communication * 0.3 + behavioral * 0.2);

  const strengths: string[] = [];
  const weaknesses: string[] = [];
  const suggestions: string[] = [];
  if (avg("technical") >= 75) strengths.push("Solid technical coverage");
  if (avg("relevance") >= 75) strengths.push("Answers stayed on topic");
  if (avg("grammar") >= 80) strengths.push("Clear written language");
  if (avg("completeness") >= 70) strengths.push("Responses had enough depth");
  if (fillerAvg >= 2) {
    weaknesses.push("High filler-word usage");
    suggestions.push("Pause instead of using fillers such as um, like, or basically");
  }
  if (avg("completeness") < 60) {
    weaknesses.push("Some answers lacked examples");
    suggestions.push("Use the STAR method: situation, task, action, result");
  }
  if (avg("keywordCoverage") < 60) {
    weaknesses.push("Low keyword coverage for the target role");
    suggestions.push("Name tools, metrics, and outcomes explicitly");
  }
  if (avg("conciseness") < 65) {
    weaknesses.push("Answers ran long");
    suggestions.push("Aim for 60–90 seconds per response");
  }
  if (!strengths.length) strengths.push("Completed a full mock session");
  if (!suggestions.length) suggestions.push("Keep practising with a higher difficulty");

  return {
    overall,
    answerQuality,
    communication,
    behavioral,
    strengths,
    weaknesses,
    suggestions,
  };
}
