package eu.arthepsy.utils;

import java.io.File;
import java.io.IOException;
import org.apache.bcel.classfile.JavaClass;
import org.apache.bcel.util.ClassPath;
import org.apache.bcel.util.SyntheticRepository;
import org.apache.bcel.Repository;

public class JavaTool {
	public static String getClassName(String filePath) throws IOException, ClassNotFoundException {
		File file = new File(filePath);
		if (! file.exists()) {
			throw new IOException("error: No such file " + file.getName());
		}
		File parent = file.getAbsoluteFile().getParentFile();
		if (parent == null || !parent.isDirectory()) {
			throw new IOException("error: No directory for file " + file.getName());
		}
		ClassPath classPath = new ClassPath(parent.getAbsolutePath());
		SyntheticRepository repository = SyntheticRepository.getInstance(classPath);
		String className = file.getName().replaceFirst("[.][^.]+$", "");

		JavaClass clazz = repository.loadClass(className);
		return clazz.getClassName();
	}

	private static void usage() { usage(false); }
	private static void usage(Boolean pathMissing) {
		StackTraceElement[] stack = Thread.currentThread().getStackTrace();
    		StackTraceElement main = stack[stack.length - 1];
    		String mainClass = main.getClassName();
		System.err.println("usage: java " + mainClass + " <command> <path>\n");
		if (pathMissing) {
			System.err.println("error: <path> is missing");
		} else {
			System.err.println("command: getClassName");
		}
		System.exit(1);
	}

	public static void main(String[] argv) {
		if (argv == null || argv.length < 2) {
			usage(argv.length > 0);
		}
		String action = argv[0];
		String filePath = argv[1];
		try {
			switch (action.toLowerCase()) {
				case "getclassname":
					String className = getClassName(filePath);
					System.out.println(filePath + ": " + className);
					break;
				default:
					usage();
					break;
			}
		} catch (Exception e) {
			System.err.println(e.getMessage());
			System.exit(1);
		}
	}
}
