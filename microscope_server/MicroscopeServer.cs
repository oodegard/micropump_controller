using System;
using System.IO;
using System.Threading;
using System.Drawing;
using System.Runtime.InteropServices;
using System.Windows.Forms;
using Newtonsoft.Json;
using System.Collections.Generic;
using Newtonsoft.Json.Linq;
using System.Drawing.Imaging;
// EmguCV
using Emgu.CV;
using Emgu.CV.CvEnum;
using Emgu.CV.Structure;

namespace MicroscopeServer
{
    /// <summary>
    /// Microscope Control Server for Windows 7 - Compatible with Python client
    /// Uses shared network folder for command/response communication
    /// </summary>
    public class MicroscopeServer
    {
        // Win32 API for mouse and keyboard control
        [DllImport("user32.dll")]
        private static extern void mouse_event(int dwFlags, int dx, int dy, int cButtons, int dwExtraInfo);
        
        [DllImport("user32.dll")]
        private static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, int dwExtraInfo);
        
        private const int MOUSEEVENTF_LEFTDOWN = 0x02;
        private const int MOUSEEVENTF_LEFTUP = 0x04;
        private const int MOUSEEVENTF_RIGHTDOWN = 0x08;
        private const int MOUSEEVENTF_RIGHTUP = 0x10;
        private const int KEYEVENTF_KEYDOWN = 0x0;
        private const int KEYEVENTF_KEYUP = 0x2;

        private string sharedFolder;
        private string commandFile;
        private string responseFile;
        private string screenshotFile;
        private string buttonsFolder;
        private bool isRunning = false;
        private const double DEFAULT_MATCH_THRESHOLD = 0.98; // High confidence threshold (accounts for minor rendering differences)

        public MicroscopeServer(string sharedPath)
        {
            // Validate and normalize path
            if (string.IsNullOrEmpty(sharedPath))
            {
                throw new ArgumentException("Shared folder path cannot be empty");
            }

            // Get full path to handle relative paths
            try
            {
                sharedFolder = Path.GetFullPath(sharedPath);
            }
            catch (Exception ex)
            {
                throw new ArgumentException(string.Format("Invalid shared folder path: {0}", ex.Message));
            }

            string statusFolder = Path.Combine(sharedFolder, "status");
            commandFile = Path.Combine(statusFolder, "command.json");
            responseFile = Path.Combine(statusFolder, "response.json");
            screenshotFile = Path.Combine(statusFolder, "screenshot.png");
            buttonsFolder = Path.Combine(sharedFolder, "buttons");
            
            // Create shared folder and status subfolder if they don't exist
            try
            {
                if (!Directory.Exists(sharedFolder))
                {
                    Directory.CreateDirectory(sharedFolder);
                    Console.WriteLine(string.Format("Created directory: {0}", sharedFolder));
                }
                if (!Directory.Exists(statusFolder))
                {
                    Directory.CreateDirectory(statusFolder);
                    Console.WriteLine(string.Format("Created status directory: {0}", statusFolder));
                }
            }
            catch (Exception ex)
            {
                throw new ArgumentException(string.Format("Cannot create shared folder: {0}", ex.Message));
            }
        }

        public void Start()
        {
            isRunning = true;
            Console.WriteLine("Remote Desktop Server Started");
            Console.WriteLine(string.Format("Shared Folder: {0}", sharedFolder));
            Console.WriteLine("Waiting for commands from client...");

            // Initialize with ready status
            UpdateResponse(new Dictionary<string, object> 
            { 
                { "status", "ready" },
                { "timestamp", DateTime.Now.ToString("o") }
            });

            // Main command loop
            long lastCommandTime = 0;
            
            while (isRunning)
            {
                try
                {
                    // Check if command file exists and has been modified
                    if (File.Exists(commandFile))
                    {
                        long currentCommandTime = File.GetLastWriteTime(commandFile).ToFileTime();
                        
                        if (currentCommandTime != lastCommandTime)
                        {
                            lastCommandTime = currentCommandTime;
                            ProcessCommand();
                        }
                    }
                    
                    Thread.Sleep(10); // Check every 10ms for fast response
                }
                catch (Exception ex)
                {
                    Console.WriteLine(string.Format("Error: {0}", ex.Message));
                    UpdateResponse(new Dictionary<string, object> 
                    { 
                        { "status", "error" },
                        { "error", ex.Message }
                    });
                }
            }
        }

        private void ProcessCommand()
        {
            dynamic cmd = ReadCommand();
            
            if (cmd == null) return;

            string action = cmd.action != null ? cmd.action.ToString() : "";
            Console.WriteLine(string.Format("Command: {0}", action));

            try
            {
                // Delete command file immediately to prevent re-execution on restart
                try
                {
                    if (File.Exists(commandFile))
                    {
                        File.Delete(commandFile);
                    }
                }
                catch (Exception ex)
                {
                    Console.WriteLine(string.Format("Warning: Could not delete command file: {0}", ex.Message));
                }

                switch (action)
                {
                    case "click":
                        int x = (int)cmd.x;
                        int y = (int)cmd.y;
                        string button = cmd.button != null ? cmd.button.ToString() : "left";
                        MouseClick(x, y, button);
                        UpdateResponse(new Dictionary<string, object> 
                        { 
                            { "status", "ok" },
                            { "action", "click" }
                        });
                        break;

                    case "type":
                        string text = cmd.text != null ? cmd.text.ToString() : "";
                        TypeText(text);
                        UpdateResponse(new Dictionary<string, object> 
                        { 
                            { "status", "ok" },
                            { "action", "type" }
                        });
                        break;

                    case "key":
                        string keyName = cmd.key != null ? cmd.key.ToString() : "";
                        PressKey(keyName);
                        UpdateResponse(new Dictionary<string, object> 
                        { 
                            { "status", "ok" },
                            { "action", "key" }
                        });
                        break;

                    case "screenshot":
                        TakeScreenshot();
                        UpdateResponse(new Dictionary<string, object> 
                        { 
                            { "status", "ok" },
                            { "action", "screenshot" },
                            { "screenshot_file", screenshotFile }
                        });
                        break;

                    case "find_and_click":
                        // Template matching to find and click button image
                        string imageName = cmd.image != null ? cmd.image.ToString() : "";
                        if (string.IsNullOrEmpty(imageName))
                        {
                            UpdateResponse(new Dictionary<string, object> 
                            { 
                                { "status", "error" },
                                { "error", "Missing 'image' parameter for find_and_click" }
                            });
                            break;
                        }
                        
                        // Add .png extension if not present
                        if (!imageName.EndsWith(".png", StringComparison.OrdinalIgnoreCase))
                        {
                            imageName += ".png";
                        }
                        
                        string buttonPath = Path.Combine(buttonsFolder, imageName);
                        
                        // Get optional confidence threshold (default 1.0 for perfect match)
                        double confidence = cmd.confidence != null ? (double)cmd.confidence : DEFAULT_MATCH_THRESHOLD;
                        
                        Point buttonLocation = FindButton(buttonPath, confidence);
                        
                        if (buttonLocation == Point.Empty)
                        {
                            UpdateResponse(new Dictionary<string, object> 
                            { 
                                { "status", "error" },
                                { "error", string.Format("Button image not found or match failed: {0}", imageName) }
                            });
                        }
                        else
                        {
                            string btnClick = cmd.button != null ? cmd.button.ToString() : "left";
                            MouseClick(buttonLocation.X, buttonLocation.Y, btnClick);
                            
                            // Send immediate "clicked" response
                            UpdateResponse(new Dictionary<string, object> 
                            { 
                                { "status", "clicked" },
                                { "action", "find_and_click" },
                                { "image", imageName },
                                { "x", buttonLocation.X },
                                { "y", buttonLocation.Y },
                                { "button", btnClick }
                            });
                            
                            // Wait for completion (default enabled with 300s timeout)
                            bool waitComplete = cmd.wait_complete == null || (bool)cmd.wait_complete;
                            int timeoutSeconds = cmd.timeout != null ? (int)cmd.timeout : 300;
                            
                            if (waitComplete)
                            {
                                WaitForButtonReturn(buttonPath, imageName, timeoutSeconds, confidence);
                            }
                        }
                        break;

                    case "shutdown":
                        isRunning = false;
                        UpdateResponse(new Dictionary<string, object> 
                        { 
                            { "status", "shutdown" }
                        });
                        break;

                    default:
                        UpdateResponse(new Dictionary<string, object> 
                        { 
                            { "status", "error" },
                            { "error", string.Format("Unknown action: {0}", action) }
                        });
                        break;
                }
            }
            catch (Exception ex)
            {
                UpdateResponse(new Dictionary<string, object> 
                { 
                    { "status", "error" },
                    { "error", ex.Message }
                });
            }
        }

        private void MouseClick(int x, int y, string button)
        {
            // Move cursor to position
            Cursor.Position = new Point(x, y);
            Thread.Sleep(10); // Minimal delay for cursor positioning

            // Simulate click
            if (button == "right")
            {
                mouse_event(MOUSEEVENTF_RIGHTDOWN, x, y, 0, 0);
                mouse_event(MOUSEEVENTF_RIGHTUP, x, y, 0, 0);
            }
            else // default to left
            {
                mouse_event(MOUSEEVENTF_LEFTDOWN, x, y, 0, 0);
                mouse_event(MOUSEEVENTF_LEFTUP, x, y, 0, 0);
            }
            
            // Move mouse away from button to prevent hover effects changing appearance
            Cursor.Position = new Point(0, 0);
            
            Console.WriteLine(string.Format("Clicked at ({0}, {1}) - {2} button", x, y, button));
        }

        private void TypeText(string text)
        {
            SendKeys.SendWait(text);
            Console.WriteLine(string.Format("Typed: {0}", text));
        }

        private void PressKey(string keyName)
        {
            // Map common key names to SendKeys format
            string sendKeysFormat = keyName;
            
            switch (keyName.ToLower())
            {
                case "enter": sendKeysFormat = "{ENTER}"; break;
                case "tab": sendKeysFormat = "{TAB}"; break;
                case "escape": sendKeysFormat = "{ESC}"; break;
                case "backspace": sendKeysFormat = "{BACKSPACE}"; break;
                case "delete": sendKeysFormat = "{DELETE}"; break;
                case "space": sendKeysFormat = " "; break;
                case "up": sendKeysFormat = "{UP}"; break;
                case "down": sendKeysFormat = "{DOWN}"; break;
                case "left": sendKeysFormat = "{LEFT}"; break;
                case "right": sendKeysFormat = "{RIGHT}"; break;
            }
            
            SendKeys.SendWait(sendKeysFormat);
            Console.WriteLine(string.Format("Pressed key: {0}", keyName));
        }

        private void TakeScreenshot()
        {
            // Take screenshot of primary screen
            Rectangle bounds = Screen.PrimaryScreen.Bounds;
            using (Bitmap screenshot = new Bitmap(bounds.Width, bounds.Height))
            {
                using (Graphics g = Graphics.FromImage(screenshot))
                {
                    g.CopyFromScreen(bounds.Location, Point.Empty, bounds.Size);
                }
                
                // Save as PNG (lossless) for perfect template matching
                screenshot.Save(screenshotFile, ImageFormat.Png);
            }
            
            Console.WriteLine(string.Format("Screenshot saved: {0}", screenshotFile));
        }

        private void SaveJpeg(Image img, string filename, long quality)
        {
            var encoderParameters = new EncoderParameters(1);
            encoderParameters.Param[0] = new EncoderParameter(System.Drawing.Imaging.Encoder.Quality, quality);
            
            var codec = GetEncoder(ImageFormat.Jpeg);
            img.Save(filename, codec, encoderParameters);
        }

        private ImageCodecInfo GetEncoder(ImageFormat format)
        {
            ImageCodecInfo[] codecs = ImageCodecInfo.GetImageDecoders();
            foreach (ImageCodecInfo codec in codecs)
            {
                if (codec.FormatID == format.Guid)
                {
                    return codec;
                }
            }
            return null;
        }

        private dynamic ReadCommand()
        {
            try
            {
                using (var file = new StreamReader(commandFile))
                {
                    return JsonConvert.DeserializeObject<dynamic>(file.ReadToEnd());
                }
            }
            catch
            {
                return null;
            }
        }

        private void UpdateResponse(Dictionary<string, object> data)
        {
            try
            {
                using (var writer = new StreamWriter(responseFile))
                {
                    writer.Write(JsonConvert.SerializeObject(data));
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine(string.Format("Failed to write response: {0}", ex.Message));
            }
        }
        
        /// <summary>
        /// Find button on screen using template matching (EmguCV)
        /// </summary>
        /// <param name="buttonPath">Path to button image template (PNG)</param>
        /// <param name="threshold">Confidence threshold (0.0-1.0, default 1.0 for perfect match)</param>
        /// <returns>Center point of button, or Point.Empty if not found</returns>
        private Point FindButton(string buttonPath, double threshold = 1.0)
        {
            try
            {
                if (!File.Exists(buttonPath))
                {
                    Console.WriteLine(string.Format("Button template not found: {0}", buttonPath));
                    return Point.Empty;
                }
                
                Console.WriteLine(string.Format("Searching for button: {0} (threshold: {1:F3})", Path.GetFileName(buttonPath), threshold));
                
                // Load the template image (the screenshot of the button)
                Image<Bgr, byte> template = new Image<Bgr, byte>(buttonPath);
                
                // Take a screenshot of the screen
                Rectangle bounds = Screen.PrimaryScreen.Bounds;
                using (Bitmap screenshot = new Bitmap(bounds.Width, bounds.Height))
                {
                    using (Graphics g = Graphics.FromImage(screenshot))
                    {
                        g.CopyFromScreen(bounds.X, bounds.Y, 0, 0, screenshot.Size);
                    }
                    
                    // Save screenshot for debugging (always save when searching)
                    try
                    {
                        screenshot.Save(screenshotFile, ImageFormat.Png);
                        Console.WriteLine(string.Format("Debug screenshot saved: {0}", screenshotFile));
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine(string.Format("Warning: Could not save debug screenshot: {0}", ex.Message));
                    }
                    
                    Image<Bgr, byte> screen = new Image<Bgr, byte>(screenshot);
                    
                    // Perform template matching to search for the button
                    Image<Gray, float> result = screen.MatchTemplate(template, TemplateMatchingType.CcoeffNormed);
                    double minVal = 0, maxVal = 0;
                    Point minLoc = new Point(), maxLoc = new Point();
                    CvInvoke.MinMaxLoc(result, ref minVal, ref maxVal, ref minLoc, ref maxLoc);
                    
                    // Check if match confidence meets or exceeds threshold
                    if (maxVal >= threshold)
                    {
                        // Calculate the center of the button
                        int centerX = maxLoc.X + template.Width / 2;
                        int centerY = maxLoc.Y + template.Height / 2;
                        
                        Console.WriteLine(string.Format("Button found at ({0}, {1}) with confidence {2:F2}", centerX, centerY, maxVal));
                        return new Point(centerX, centerY);
                    }
                    else
                    {
                        Console.WriteLine(string.Format("Button not found (confidence: {0:F2}, threshold: {1:F2})", maxVal, threshold));
                        return Point.Empty;
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine(string.Format("Error finding button: {0}", ex.Message));
                return Point.Empty;
            }
        }
        
        /// <summary>
        /// Wait for button to return after clicking (monitors acquisition completion).
        /// </summary>
        /// <param name="buttonPath">Path to button template image</param>
        /// <param name="imageName">Name of button image for logging</param>
        /// <param name="timeoutSeconds">Maximum time to wait in seconds</param>
        /// <param name="confidence">Confidence threshold for button detection (0.0-1.0)</param>
        private void WaitForButtonReturn(string buttonPath, string imageName, int timeoutSeconds, double confidence)
        {
            Console.WriteLine(string.Format("Monitoring button return for up to {0} seconds...", timeoutSeconds));
            
            // Initial delay to let UI update (button gets greyed/disabled)
            Thread.Sleep(500);
            
            DateTime startTime = DateTime.Now;
            int pollIntervalMs = 200; // Check every 200ms
            int maxAttempts = (timeoutSeconds * 1000) / pollIntervalMs;
            
            for (int i = 0; i < maxAttempts; i++)
            {
                Point btn = FindButton(buttonPath, confidence);
                
                if (btn != Point.Empty)
                {
                    // Button is back - acquisition complete
                    double elapsedSeconds = (DateTime.Now - startTime).TotalSeconds;
                    Console.WriteLine(string.Format("Button returned after {0:F1} seconds - acquisition complete", elapsedSeconds));
                    
                    UpdateResponse(new Dictionary<string, object> 
                    { 
                        { "status", "complete" },
                        { "action", "find_and_click" },
                        { "image", imageName },
                        { "duration_seconds", Math.Round(elapsedSeconds, 1) }
                    });
                    return;
                }
                
                Thread.Sleep(pollIntervalMs);
            }
            
            // Timeout reached
            double timeoutElapsed = (DateTime.Now - startTime).TotalSeconds;
            Console.WriteLine(string.Format("Button did not return within {0} seconds - timeout", timeoutElapsed));
            
            UpdateResponse(new Dictionary<string, object> 
            { 
                { "status", "timeout" },
                { "action", "find_and_click" },
                { "image", imageName },
                { "waited_seconds", Math.Round(timeoutElapsed, 1) },
                { "error", string.Format("Button did not return within {0} seconds", timeoutSeconds) }
            });
        }
    }

    class Program
    {
        // Win32 API for DPI awareness
        [DllImport("user32.dll")]
        private static extern bool SetProcessDPIAware();
        
        static void Main(string[] args)
        {
            // Enable DPI awareness to get true screen resolution
            try
            {
                SetProcessDPIAware();
            }
            catch
            {
                // Ignore if not supported (older Windows versions)
            }
            
            Console.WriteLine("=== Microscope Control Server for Windows 7 ===");
            Console.WriteLine("Compatible with Python microscope client");
            Console.WriteLine();

            // Default to current directory if no argument provided
            string sharedPath = Environment.CurrentDirectory;
            
            if (args.Length > 0 && !string.IsNullOrEmpty(args[0]))
            {
                sharedPath = args[0];
            }

            Console.WriteLine(string.Format("Using shared folder: {0}", sharedPath));
            Console.WriteLine("Press Ctrl+C to exit");
            Console.WriteLine();

            try
            {
                var server = new MicroscopeServer(sharedPath);
                server.Start();
            }
            catch (ArgumentException ex)
            {
                Console.WriteLine(string.Format("ERROR: {0}", ex.Message));
                Console.WriteLine();
                Console.WriteLine("Usage: MicroscopeServer.exe [shared_folder_path]");
                Console.WriteLine("Example: MicroscopeServer.exe C:\\SharedFolder");
                Console.WriteLine("Example: MicroscopeServer.exe \\\\SERVER\\SharedFolder");
                Console.WriteLine();
                Console.WriteLine("Press any key to exit...");
                Console.ReadKey();
                Environment.Exit(1);
            }
            catch (Exception ex)
            {
                Console.WriteLine(string.Format("FATAL ERROR: {0}", ex.Message));
                Console.WriteLine(string.Format("Stack trace: {0}", ex.StackTrace));
                Console.WriteLine();
                Console.WriteLine("Press any key to exit...");
                Console.ReadKey();
                Environment.Exit(1);
            }
        }
    }
}
