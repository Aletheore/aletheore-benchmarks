import java.io.*;

public class DiffTests {

    // --- 013: gson-jsonprimitive-hashcode ---
    // isIntegral branch. OLD always routes through the double value (loses
    // precision above 2^53, but stays consistent with the "instanceof Number"
    // branch for cross-type equals()). NEW hashes the exact long value
    // directly - fine per-value, but diverges from OLD for any long beyond
    // double's exact-integer range, which is exactly where the real
    // equals/hashCode contract violation this fix addressed shows up.
    static int hashOfDoubleValue(double doubleValue) {
        long longValue = (long) doubleValue;
        if (doubleValue == longValue) {
            return (int) (longValue ^ (longValue >>> 32));
        }
        long bits = Double.doubleToLongBits(doubleValue);
        return (int) (bits ^ (bits >>> 32));
    }
    static int hash013_old(long longValue, double doubleValueOfSameLong) {
        return hashOfDoubleValue(doubleValueOfSameLong);
    }
    static int hash013_new(long longValue) {
        long v = longValue;
        return (int) (v ^ (v >>> 32));
    }
    static String test013() {
        long bigLong = 9007199254740993L; // 2^53 + 1 - not exactly representable as double
        double asDouble = (double) bigLong; // real getAsNumber().doubleValue() behavior
        int oldHash = hash013_old(bigLong, asDouble);
        int newHash = hash013_new(bigLong);
        if (oldHash != newHash) {
            return "DIVERGED\tlong=" + bigLong + " (doubleValue()=" + asDouble + ") old_hash=" + oldHash + " new_hash=" + newHash;
        }
        return "IDENTICAL\t";
    }

    // --- 014: junit4-assumption-serialization ---
    // Minimal repro of AssumptionViolatedException's custom writeObject
    // (wraps a non-Serializable field) vs relying on default serialization.
    static class NotSerializableThing {
        String label;
        NotSerializableThing(String l) { label = l; }
        public String toString() { return "NotSerializableThing(" + label + ")"; }
    }
    static class SerializableWrapper implements Serializable {
        private final String s;
        SerializableWrapper(Object o) { this.s = String.valueOf(o); }
        public String toString() { return s; }
    }
    static class Exc_old extends RuntimeException {
        Object fValue;
        Exc_old(Object v) { super("assumption"); fValue = v; }
        private void writeObject(ObjectOutputStream oos) throws IOException {
            ObjectOutputStream.PutField pf = oos.putFields();
            pf.put("fValue", fValue instanceof Serializable || fValue == null
                ? fValue : new SerializableWrapper(fValue));
            oos.writeFields();
        }
    }
    static class Exc_new extends RuntimeException {
        Object fValue;
        Exc_new(Object v) { super("assumption"); fValue = v; }
        // no writeObject override - default serialization touches fValue directly
    }
    static String test014() {
        NotSerializableThing thing = new NotSerializableThing("matcher-desc");
        String oldResult, newResult;
        try {
            ByteArrayOutputStream bos = new ByteArrayOutputStream();
            new ObjectOutputStream(bos).writeObject(new Exc_old(thing));
            oldResult = "ok (" + bos.size() + " bytes)";
        } catch (Exception e) {
            oldResult = "raised " + e.getClass().getSimpleName();
        }
        try {
            ByteArrayOutputStream bos = new ByteArrayOutputStream();
            new ObjectOutputStream(bos).writeObject(new Exc_new(thing));
            newResult = "ok (" + bos.size() + " bytes)";
        } catch (Exception e) {
            newResult = "raised " + e.getClass().getSimpleName();
        }
        if (!oldResult.equals(newResult)) {
            return "DIVERGED\tserializing exception wrapping a non-Serializable value: old=" + oldResult + " new=" + newResult;
        }
        return "IDENTICAL\t";
    }

    // --- 015: commons-lang-bitfield-sign-extension ---
    static int getValue_old(int rawMaskedValue, int shiftCount) {
        return rawMaskedValue >>> shiftCount;
    }
    static int getValue_new(int rawMaskedValue, int shiftCount) {
        return rawMaskedValue >> shiftCount;
    }
    static String test015() {
        // Field occupying the top byte (mask 0xFF000000, shiftCount 24) -
        // getRawValue's real output for a holder with that byte = 0xFF is
        // exactly 0xFF000000 (bit 31 set), the top-bit-aligned case the
        // real bug affects.
        int rawMaskedValue = 0xFF000000;
        int old = getValue_old(rawMaskedValue, 24);
        int neu = getValue_new(rawMaskedValue, 24);
        if (old != neu) {
            return "DIVERGED\trawMaskedValue=0x" + Integer.toHexString(rawMaskedValue)
                + " shiftCount=24 old=" + old + " new=" + neu;
        }
        return "IDENTICAL\t";
    }

    public static void main(String[] args) {
        System.out.printf("%-45s %s%n", "013-gson-jsonprimitive-hashcode", test013());
        System.out.printf("%-45s %s%n", "014-junit4-assumption-serialization", test014());
        System.out.printf("%-45s %s%n", "015-commons-lang-bitfield-sign-extension", test015());
    }
}
