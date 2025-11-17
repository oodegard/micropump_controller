# Button Templates for Template Matching

Put PNG screenshots of buttons here for the C# server to find and click.

## Quick Start

1. Screenshot your microscope software Run button
2. Crop just the button
3. Save as `run.png` in this folder  
4. Use `microscope: run` in YAML - server finds and clicks it automatically

## How Template Matching Works

1. Server loads `buttons/run.png`
2. Takes screenshot of microscope PC
3. Uses EmguCV template matching (0.8 confidence threshold)
4. Clicks center of matched region

## Creating Good Button Templates

✅ **Good:** 30-100px, high contrast, includes distinctive text/icon
❌ **Bad:** Too generic, low contrast, too large/small

## See EMGUCV_SETUP.md for installation instructions
