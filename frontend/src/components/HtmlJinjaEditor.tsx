import { useEffect, useMemo } from "react";
import { useEditor, EditorContent, Node as TiptapNode, mergeAttributes } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";

// Custom Tiptap Node Extension to represent Jinja tokens (expressions and statements)
const JinjaToken = TiptapNode.create({
  name: "jinjaToken",
  group: "inline",
  inline: true,
  selectable: true,
  atom: true,

  addAttributes() {
    return {
      "data-jinja-raw": {
        default: null,
      },
      class: {
        default: null,
      },
      contenteditable: {
        default: "false",
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: "span[data-jinja-raw]",
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return ["span", mergeAttributes(HTMLAttributes), 0];
  },
});

// Helper: Convert Jinja tags into HTML comments/spans to prevent browser fostering
function templateToHtml(template: string): string {
  if (!template) return "";

  const parser = new DOMParser();
  const doc = parser.parseFromString(template, "text/html");

  const walk = (parent: globalThis.Node) => {
    const children = Array.from(parent.childNodes);
    for (const child of children) {
      if (child.nodeType === globalThis.Node.TEXT_NODE) {
        const text = child.nodeValue || "";
        if (text.includes("{%") || text.includes("{{")) {
          const fragment = doc.createDocumentFragment();
          const parts = text.split(/(\{%[\s\S]*?%\})|(\{\{[\s\S]*?\}\})/g);

          for (let i = 0; i < parts.length; i++) {
            const part = parts[i];
            if (part === undefined || part === "") continue;

            if (part.startsWith("{%") && part.endsWith("%}")) {
              const encoded = btoa(unescape(encodeURIComponent(part)));
              const commentNode = doc.createComment(`JINJA_STMT:${encoded}`);
              fragment.appendChild(commentNode);
            } else if (part.startsWith("{{") && part.endsWith("}}")) {
              const encoded = btoa(unescape(encodeURIComponent(part)));
              const span = doc.createElement("span");
              span.className = "jinja-expression bg-surface-container-highest text-on-surface px-xs py-0.5 rounded font-mono text-xs mx-0.5 select-none";
              span.textContent = part;
              span.setAttribute("contenteditable", "false");
              span.setAttribute("data-jinja-raw", encoded);
              fragment.appendChild(span);
            } else {
              fragment.appendChild(doc.createTextNode(part));
            }
          }
          child.replaceWith(fragment);
        }
      } else if (child.nodeType === globalThis.Node.ELEMENT_NODE) {
        const el = child as HTMLElement;
        const tagName = el.tagName.toLowerCase();
        if (tagName !== "script" && tagName !== "style") {
          walk(child);
        }
      }
    }
  };

  walk(doc.body);

  const hasHtmlTag = /<html/i.test(template);
  if (hasHtmlTag) {
    return "<!DOCTYPE html>\n" + doc.documentElement.outerHTML;
  } else {
    return doc.body.innerHTML;
  }
}

// Helper: Convert comments/spans back to Jinja tags
function htmlToTemplate(html: string): string {
  if (!html) return "";

  let result = html;

  // 1. Decode statement comments
  result = result.replace(/<!--\s*JINJA_STMT:([A-Za-z0-9+/=]+)\s*-->/g, (match, encoded) => {
    try {
      return decodeURIComponent(escape(atob(encoded)));
    } catch (e) {
      console.error("Failed to decode Jinja statement comment", e);
      return match;
    }
  });

  // 2. Decode expression spans
  result = result.replace(/<span[^>]*?data-jinja-raw="([^"]+)"[^>]*?>[\s\S]*?<\/span>/g, (match, encoded) => {
    try {
      return decodeURIComponent(escape(atob(encoded)));
    } catch (e) {
      console.error("Failed to decode Jinja expression span", e);
      return match;
    }
  });

  return result;
}

interface HtmlJinjaEditorProps {
  value: string;
  onChange: (val: string) => void;
  css?: string;
  onDropToken?: () => void;
}

export default function HtmlJinjaEditor({ value, onChange, css, onDropToken }: HtmlJinjaEditorProps) {
  // Scope CSS to only apply inside the visual canvas root wrapper
  const scopedCss = useMemo(() => {
    if (!css) return "";
    return css.replace(/([^\r\n,{}]+)(?=[^{]*\{)/g, (match) => {
      const trimmed = match.trim();
      if (trimmed.startsWith("@")) return trimmed; // Skip media queries
      return trimmed.split(",").map(selector => `#visual-canvas-root ${selector.trim()}`).join(", ");
    });
  }, [css]);

  const editor = useEditor({
    extensions: [StarterKit, JinjaToken],
    content: templateToHtml(value),
    onUpdate: ({ editor }) => {
      const currentHtml = htmlToTemplate(editor.getHTML());
      onChange(currentHtml);
    },
    editorProps: {
      attributes: {
        class: "w-full min-h-[800px] focus:outline-none prose max-w-none p-xl",
      },
      handleDrop: (_view, event, _slice, _moved) => {
        // Handle drag and drop of tokens from left panel
        const token = event.dataTransfer?.getData("text/plain");
        if (!token) return false;

        event.preventDefault();

        // Get coordinates where the token was dropped
        const coordinates = _view.posAtCoords({ left: event.clientX, top: event.clientY });
        if (!coordinates) return false;

        const isExpression = token.includes("for") || token.includes("endfor") || token.includes("if");
        const encoded = btoa(unescape(encodeURIComponent(token)));
        const className = isExpression
          ? "jinja-statement bg-primary-fixed text-primary px-xs py-0.5 rounded font-mono text-xs mx-0.5 select-none"
          : "jinja-expression bg-surface-container-highest text-on-surface px-xs py-0.5 rounded font-mono text-xs mx-0.5 select-none";

        // Insert at coordinates position
        editor?.commands.insertContentAt(coordinates.pos, {
          type: "jinjaToken",
          attrs: {
            "data-jinja-raw": encoded,
            class: className,
            contenteditable: "false",
          },
        });

        if (onDropToken) {
          onDropToken();
        }

        return true;
      },
    },
  });

  // Keep editor content in sync with external values if changed externally
  useEffect(() => {
    if (!editor) return;
    const currentHtml = htmlToTemplate(editor.getHTML());
    if (currentHtml !== value) {
      editor.commands.setContent(templateToHtml(value));
    }
  }, [value, editor]);

  return (
    <div id="visual-canvas-root" className="w-full max-w-[800px] bg-white min-h-[1056px] shadow-lg rounded border border-outline-variant flex flex-col relative overflow-hidden">
      {css && <style dangerouslySetInnerHTML={{ __html: scopedCss }} />}
      <EditorContent editor={editor} className="flex-1 w-full" />
    </div>
  );
}
