package android.content;

/** JVM test double only; never packaged. */
public abstract class Context {
    public Context getApplicationContext() { return this; }
    public abstract SharedPreferences getSharedPreferences(String name, int mode);
}
