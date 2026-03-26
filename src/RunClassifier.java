import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

/** Protected Java JSON adapter for Stage 2. */
public final class RunClassifier {

    private RunClassifier() {
    }

    public static void main(String[] args) throws Exception {
        JsonUtil.Request request = JsonUtil.readRequest(System.in);

        PrintStream originalOut = System.out;
        ByteArrayOutputStream capturedStdout = new ByteArrayOutputStream();
        List<JsonUtil.ResultRecord> results;

        try (PrintStream trap = new PrintStream(capturedStdout, true, StandardCharsets.UTF_8.name())) {
            System.setOut(trap);
            results = new ArrayList<>();
            for (JsonUtil.CaseRecord c : request.cases) {
                String[] decision = NumericLiteralClassifier.classifyNumLit(c.input);
                if (decision == null || decision.length != 2) {
                    throw new IllegalStateException(
                        "NumericLiteralClassifier.classifyNumLit(inputText) must return "
                        + "a 2-item array: [actual, actualKind]."
                    );
                }
                String actual = decision[0];
                String actualKind = "Accept".equals(actual) ? decision[1] : "-";
                results.add(new JsonUtil.ResultRecord(c.caseId, actual, actualKind));
            }
        } finally {
            System.setOut(originalOut);
        }

        String suppressed = capturedStdout.toString(StandardCharsets.UTF_8.name()).trim();
        if (!suppressed.isEmpty()) {
            System.err.println(
                "WARNING: stdout generated inside NumericLiteralClassifier was suppressed. "
                + "Use stderr for debugging output."
            );
            System.err.println(suppressed);
        }

        JsonUtil.writeResponse(System.out, results);
    }
}