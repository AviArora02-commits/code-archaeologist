import type { ReactNode } from "react";

/** Lightweight markdown-ish renderer for Cognee answers (no extra deps). */

function inlineFormat(text: string): ReactNode[] {
  const parts: ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let last = 0;
  let match: RegExpExecArray | null;
  let key = 0;
  while ((match = re.exec(text)) !== null) {
    if (match.index > last) parts.push(text.slice(last, match.index));
    const token = match[0];
    if (token.startsWith("**")) {
      parts.push(
        <strong key={key++} className="font-semibold text-slate-100">
          {token.slice(2, -2)}
        </strong>
      );
    } else {
      parts.push(
        <code
          key={key++}
          className="rounded bg-slate-800/80 px-1.5 py-0.5 font-mono text-xs text-cyan-300"
        >
          {token.slice(1, -1)}
        </code>
      );
    }
    last = match.index + token.length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

export function AnswerView({ text }: { text: string }) {
  const lines = text.split("\n");

  return (
    <div className="space-y-3 text-sm leading-relaxed text-slate-300">
      {lines.map((line, i) => {
        const trimmed = line.trim();
        if (!trimmed) return <div key={i} className="h-2" />;

        if (trimmed.startsWith("### ")) {
          return (
            <h4 key={i} className="pt-2 font-serif text-base text-slate-100">
              {trimmed.slice(4)}
            </h4>
          );
        }
        if (trimmed.startsWith("## ")) {
          return (
            <h3 key={i} className="pt-2 font-serif text-lg text-slate-100">
              {trimmed.slice(3)}
            </h3>
          );
        }
        if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
          return (
            <div key={i} className="flex gap-2 pl-1">
              <span className="text-sky-400">•</span>
              <p>{inlineFormat(trimmed.slice(2))}</p>
            </div>
          );
        }
        const numbered = trimmed.match(/^(\d+)\.\s+(.*)/);
        if (numbered) {
          return (
            <div key={i} className="flex gap-2 pl-1">
              <span className="font-mono text-xs text-sky-400">{numbered[1]}.</span>
              <p>{inlineFormat(numbered[2])}</p>
            </div>
          );
        }
        return <p key={i}>{inlineFormat(trimmed)}</p>;
      })}
    </div>
  );
}
