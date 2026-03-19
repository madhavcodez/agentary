interface DossierViewProps {
  contentMd: string;
}

interface Section {
  heading: string;
  body: string;
}

function parseMarkdown(md: string): Section[] {
  const lines = md.split("\n");
  const sections: Section[] = [];
  let currentHeading = "";
  let currentBody: string[] = [];

  for (const line of lines) {
    const headingMatch = line.match(/^##\s+(.+)/);
    if (headingMatch) {
      if (currentHeading || currentBody.length > 0) {
        sections.push({
          heading: currentHeading,
          body: currentBody.join("\n").trim(),
        });
      }
      currentHeading = headingMatch[1];
      currentBody = [];
    } else {
      currentBody.push(line);
    }
  }

  if (currentHeading || currentBody.length > 0) {
    sections.push({
      heading: currentHeading,
      body: currentBody.join("\n").trim(),
    });
  }

  return sections;
}

function renderBody(text: string) {
  const lines = text.split("\n");

  return lines.map((line, i) => {
    if (line.startsWith("### ")) {
      return (
        <h4 key={i} className="text-sm font-semibold text-gray-200 mt-4 mb-2">
          {line.replace("### ", "")}
        </h4>
      );
    }

    if (line.startsWith("- ") || line.startsWith("* ")) {
      return (
        <li key={i} className="text-sm text-gray-400 ml-4 list-disc leading-relaxed">
          {renderInlineMarkdown(line.slice(2))}
        </li>
      );
    }

    if (line.startsWith("**") && line.endsWith("**")) {
      return (
        <p key={i} className="text-sm font-semibold text-gray-200 mt-2">
          {line.replace(/\*\*/g, "")}
        </p>
      );
    }

    if (line.trim() === "") {
      return <div key={i} className="h-2" />;
    }

    return (
      <p key={i} className="text-sm text-gray-400 leading-relaxed">
        {renderInlineMarkdown(line)}
      </p>
    );
  });
}

function renderInlineMarkdown(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <span key={i} className="font-semibold text-gray-200">
          {part.replace(/\*\*/g, "")}
        </span>
      );
    }
    return part;
  });
}

export default function DossierView({ contentMd }: DossierViewProps) {
  const sections = parseMarkdown(contentMd);

  if (sections.length === 0) {
    return (
      <div className="text-gray-500 text-sm py-8 text-center">
        No dossier content available.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {sections.map((section, idx) => (
        <div key={idx} className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          {section.heading && (
            <h3 className="text-base font-semibold text-indigo-400 mb-3 pb-2 border-b border-gray-800">
              {section.heading}
            </h3>
          )}
          <div>{renderBody(section.body)}</div>
        </div>
      ))}
    </div>
  );
}
