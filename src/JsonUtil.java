import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Protected JSON helper for the Stage 2 Java path. */
public final class JsonUtil {

    public static final int REQUEST_VERSION = 1;

    public static final class CaseRecord {
        public final String caseId;
        public final String inputRaw;
        public final String input;
        public final String expected;
        public final String kind;

        public CaseRecord(String caseId, String inputRaw, String input, String expected, String kind) {
            this.caseId = caseId;
            this.inputRaw = inputRaw;
            this.input = input;
            this.expected = expected;
            this.kind = kind;
        }
    }

    public static final class ResultRecord {
        public final String caseId;
        public final String actual;
        public final String actualKind;

        public ResultRecord(String caseId, String actual, String actualKind) {
            this.caseId = caseId;
            this.actual = actual;
            this.actualKind = actualKind;
        }
    }

    public static final class Request {
        public final int version;
        public final List<CaseRecord> cases;

        public Request(int version, List<CaseRecord> cases) {
            this.version = version;
            this.cases = cases;
        }
    }

    private JsonUtil() {
    }

    public static Request readRequest(InputStream input) throws IOException {
        String text = new String(input.readAllBytes(), StandardCharsets.UTF_8);
        Object value = new Parser(text).parse();
        if (!(value instanceof Map)) {
            throw new IOException("Stage 2 request must be a JSON object.");
        }

        @SuppressWarnings("unchecked")
        Map<String, Object> root = (Map<String, Object>) value;
        int version = requireInt(root, "version");
        if (version != REQUEST_VERSION) {
            throw new IOException(
                "Unsupported request version " + version + ". Expected " + REQUEST_VERSION + "."
            );
        }

        Object casesValue = root.get("cases");
        if (!(casesValue instanceof List)) {
            throw new IOException("Request JSON must contain an array under 'cases'.");
        }

        @SuppressWarnings("unchecked")
        List<Object> rawCases = (List<Object>) casesValue;
        List<CaseRecord> cases = new ArrayList<>();
        for (Object item : rawCases) {
            if (!(item instanceof Map)) {
                throw new IOException("Each case entry must be a JSON object.");
            }
            @SuppressWarnings("unchecked")
            Map<String, Object> rawCase = (Map<String, Object>) item;
            cases.add(
                new CaseRecord(
                    requireString(rawCase, "case_id"),
                    requireString(rawCase, "input_raw"),
                    requireString(rawCase, "input"),
                    requireString(rawCase, "expected"),
                    requireString(rawCase, "kind")
                )
            );
        }

        return new Request(version, cases);
    }

    public static void writeResponse(OutputStream output, List<ResultRecord> results) throws IOException {
        StringBuilder sb = new StringBuilder();
        sb.append('{');
        sb.append("\"version\":").append(REQUEST_VERSION).append(',');
        sb.append("\"results\":[");
        for (int i = 0; i < results.size(); i++) {
            ResultRecord result = results.get(i);
            if (i > 0) {
                sb.append(',');
            }
            sb.append('{');
            sb.append("\"case_id\":\"").append(escapeJson(result.caseId)).append("\",");
            sb.append("\"actual\":\"").append(escapeJson(result.actual)).append("\",");
            sb.append("\"actual_kind\":\"").append(escapeJson(result.actualKind)).append("\"");
            sb.append('}');
        }
        sb.append("]}\n");
        output.write(sb.toString().getBytes(StandardCharsets.UTF_8));
        output.flush();
    }

    private static String requireString(Map<String, Object> obj, String key) throws IOException {
        Object value = obj.get(key);
        if (value instanceof String) {
            return (String) value;
        }
        throw new IOException("Missing or invalid string field '" + key + "'.");
    }

    private static int requireInt(Map<String, Object> obj, String key) throws IOException {
        Object value = obj.get(key);
        if (value instanceof Number) {
            return ((Number) value).intValue();
        }
        throw new IOException("Missing or invalid integer field '" + key + "'.");
    }

    private static String escapeJson(String value) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < value.length(); i++) {
            char ch = value.charAt(i);
            switch (ch) {
                case '\\':
                    sb.append("\\\\");
                    break;
                case '"':
                    sb.append("\\\"");
                    break;
                case '\b':
                    sb.append("\\b");
                    break;
                case '\f':
                    sb.append("\\f");
                    break;
                case '\n':
                    sb.append("\\n");
                    break;
                case '\r':
                    sb.append("\\r");
                    break;
                case '\t':
                    sb.append("\\t");
                    break;
                default:
                    if (ch < 0x20) {
                        sb.append(String.format("\\u%04x", (int) ch));
                    } else {
                        sb.append(ch);
                    }
                    break;
            }
        }
        return sb.toString();
    }

    private static final class Parser {
        private final String text;
        private int index;

        Parser(String text) {
            this.text = text;
            this.index = 0;
        }

        Object parse() throws IOException {
            Object value = parseValue();
            skipWhitespace();
            if (index != text.length()) {
                throw error("Unexpected trailing content");
            }
            return value;
        }

        private Object parseValue() throws IOException {
            skipWhitespace();
            if (index >= text.length()) {
                throw error("Unexpected end of JSON input");
            }
            char ch = text.charAt(index);
            if (ch == '{') {
                return parseObject();
            }
            if (ch == '[') {
                return parseArray();
            }
            if (ch == '"') {
                return parseString();
            }
            if (ch == '-' || Character.isDigit(ch)) {
                return parseNumber();
            }
            if (text.startsWith("true", index)) {
                index += 4;
                return Boolean.TRUE;
            }
            if (text.startsWith("false", index)) {
                index += 5;
                return Boolean.FALSE;
            }
            if (text.startsWith("null", index)) {
                index += 4;
                return null;
            }
            throw error("Unexpected token");
        }

        private Map<String, Object> parseObject() throws IOException {
            expect('{');
            LinkedHashMap<String, Object> obj = new LinkedHashMap<>();
            skipWhitespace();
            if (peek('}')) {
                expect('}');
                return obj;
            }
            while (true) {
                String key = parseString();
                skipWhitespace();
                expect(':');
                Object value = parseValue();
                obj.put(key, value);
                skipWhitespace();
                if (peek('}')) {
                    expect('}');
                    return obj;
                }
                expect(',');
            }
        }

        private List<Object> parseArray() throws IOException {
            expect('[');
            ArrayList<Object> items = new ArrayList<>();
            skipWhitespace();
            if (peek(']')) {
                expect(']');
                return items;
            }
            while (true) {
                items.add(parseValue());
                skipWhitespace();
                if (peek(']')) {
                    expect(']');
                    return items;
                }
                expect(',');
            }
        }

        private String parseString() throws IOException {
            expect('"');
            StringBuilder sb = new StringBuilder();
            while (index < text.length()) {
                char ch = text.charAt(index++);
                if (ch == '"') {
                    return sb.toString();
                }
                if (ch == '\\') {
                    if (index >= text.length()) {
                        throw error("Unterminated escape sequence");
                    }
                    char esc = text.charAt(index++);
                    switch (esc) {
                        case '"':
                            sb.append('"');
                            break;
                        case '\\':
                            sb.append('\\');
                            break;
                        case '/':
                            sb.append('/');
                            break;
                        case 'b':
                            sb.append('\b');
                            break;
                        case 'f':
                            sb.append('\f');
                            break;
                        case 'n':
                            sb.append('\n');
                            break;
                        case 'r':
                            sb.append('\r');
                            break;
                        case 't':
                            sb.append('\t');
                            break;
                        case 'u':
                            sb.append(parseUnicodeEscape());
                            break;
                        default:
                            throw error("Unsupported escape sequence");
                    }
                } else {
                    sb.append(ch);
                }
            }
            throw error("Unterminated string literal");
        }

        private char parseUnicodeEscape() throws IOException {
            if (index + 4 > text.length()) {
                throw error("Invalid unicode escape");
            }
            String hex = text.substring(index, index + 4);
            index += 4;
            try {
                return (char) Integer.parseInt(hex, 16);
            } catch (NumberFormatException exc) {
                throw error("Invalid unicode escape");
            }
        }

        private Number parseNumber() throws IOException {
            int start = index;
            if (text.charAt(index) == '-') {
                index++;
            }
            while (index < text.length() && Character.isDigit(text.charAt(index))) {
                index++;
            }
            boolean isFloat = false;
            if (index < text.length() && text.charAt(index) == '.') {
                isFloat = true;
                index++;
                while (index < text.length() && Character.isDigit(text.charAt(index))) {
                    index++;
                }
            }
            if (index < text.length()) {
                char ch = text.charAt(index);
                if (ch == 'e' || ch == 'E') {
                    isFloat = true;
                    index++;
                    if (index < text.length()) {
                        char sign = text.charAt(index);
                        if (sign == '+' || sign == '-') {
                            index++;
                        }
                    }
                    while (index < text.length() && Character.isDigit(text.charAt(index))) {
                        index++;
                    }
                }
            }
            String token = text.substring(start, index);
            try {
                return isFloat ? Double.valueOf(token) : Integer.valueOf(token);
            } catch (NumberFormatException exc) {
                throw error("Invalid number literal");
            }
        }

        private void skipWhitespace() {
            while (index < text.length() && Character.isWhitespace(text.charAt(index))) {
                index++;
            }
        }

        private boolean peek(char ch) {
            return index < text.length() && text.charAt(index) == ch;
        }

        private void expect(char ch) throws IOException {
            skipWhitespace();
            if (index >= text.length() || text.charAt(index) != ch) {
                throw error("Expected '" + ch + "'");
            }
            index++;
        }

        private IOException error(String message) {
            return new IOException(message + " near position " + index + ".");
        }
    }
}