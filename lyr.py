#!/usr/bin/python3

'lyr.py: Description of what lyr does.'

__author__      = 'Marco Torres'
__copyright__   = 'Copyright 2009, Planet Earth'


# Imports
import os
import sys
import json
import subprocess
from shutil import copyfile
from optparse import OptionParser


# Global variables
usage = 'Usage: lyr.py --lyrics/-l nessun_dorma.txt'
font_syntax={'init': '\\def\\fsize{', 'end': '}'}
background_syntax={'init': '{\n\\usebackgroundtemplate{\\includegraphics[height=\\paperwidth]{../images/', 'mid': '}}\n', 'end': '}\n'}
frame_syntax={'init': '\\begin{frame}{}\n', 'end': '\end{frame}\n'}
block_syntax={'init': '\\begin{block}{}\n', 'end': '\\end{block}\n'}
tikz_syntax={'init': '\\begin{tikzpicture}\n', 'end': '\\end{tikzpicture}\n'}
centering='\\centering\n'
format_font='\\formatfont\n'
blur={'init': '\\blurry{', 'mid': '}{\\rowh*', 'end': '}\n'}


def main():
	# Parse input parameters
	global usage
	parser = OptionParser(usage)
	parser.add_option('-f','--file', help='Lyrics file name', type='str' )
	parser.add_option('-u','--unlock_caps', help='Unlock capitals for all text', action='store_true' ,default=False)
	parser.add_option('-m','--mute_pdf', help='Avoid pdf generation', action='store_true' ,default=False)
	parser.add_option('-d','--draft', help='Avoid pdf complex graphics generation', action='store_true' ,default=False)
	parser.add_option('--debug', help='Print debug messages', action='store_true' ,default=False)
	(options,args) = parser.parse_args()

	# Format given lyrics
	if options.file is not None:
		lyrics = lyr_get(options.file)
		tex_file = lyr_format(lyrics, options)
		if not options.mute_pdf:
			for _ in range(2):
				lyr_pdflatex(tex_file, options)
			lyr_clean(tex_file)
			lyr_resize(tex_file)
	print('Status: Process completed')


def lyr_get(file_name):
	print('Status: Parsing lyrics of {} ... '.format(file_name))
	with open(file_name) as data_file:
		try:
			lyrics = json.load(data_file)
		except Exception as err:
			print('Error: Syntax error in {}, {}.'.format(file_name, err))
			os._exit(1)
	return lyrics


def lyr_format(lyrics, options):
	print('Status: Giving format ... ')
	tex_file_name = 'out/'+options.file[7:-4]+'.tex'
	copyfile('ref/template.tex', tex_file_name)
	tex_file = open(tex_file_name, 'w')

	# Get number of posible blocks per frame
	frames = []
	frame = []
	rows_per_frame = int(200 / int(lyrics['font_size']))
	if options.debug:
		print('Debug: Rows per frame = {}'.format(rows_per_frame))
	available_rows = rows_per_frame

	for block_index, block_name in enumerate(lyrics['order']):

		# Define block length
		block_len = len(lyrics[block_name])
		if options.debug:
			print('Debug: Rows of {} = {}.'.format(block_name, block_len))
			print('Debug: Available rows in frame = {}.'.format(available_rows))
		if block_len > rows_per_frame:
			# TODO: Split block
			print('Error: Font is too large, define a smaller.')
			return

		# Allocate blocks in frames
		while True:
			if available_rows >= block_len:
				frame.append(block_name)
				available_rows -= block_len
				if options.debug:
					print('Debug: Frame = {}.'.format(frame))
				break
			else:
				frames.append(frame[:])
				frame = []
				available_rows = rows_per_frame
				if options.debug:
					print('Debug: End of frame.\n')

	if len(frame) != 0:
		frames.append(frame[:])
		if options.debug:
			print('Debug: End of frame.\n')
			print('Debug: Frames = {}.\n'.format(frames))

	with open('ref/template.tex') as src:
		with open(tex_file_name, 'w') as dst:
			for line in src:
				if '%lyr_font_size' in line:
					dst.write('{}{}{}'.format(font_syntax['init'],
											  lyrics['font_size'],
											  font_syntax['end']))
				elif '%lyr_text' in line:
					dst.write('{}{}{}'.format(background_syntax['init'],
											  lyrics['image'],
											  background_syntax['mid']))
					for frame in frames:
						dst.write(frame_syntax['init'])
						dst.write(format_font)
						for block_name in frame:
							dst.write(block_syntax['init'])
							dst.write(centering)
							dst.write(tikz_syntax['init'])
							k = len(lyrics[block_name])
							for i, row in enumerate(lyrics[block_name]):
								if not options.unlock_caps:
									row = row.upper()
								if not options.draft:
									row = '{}{}{}{}{}'.format(blur['init'],
															row, blur['mid'],
															k-i-1,
															blur['end'])
								dst.write(row)
							dst.write(tikz_syntax['end'])
							dst.write(block_syntax['end'])
						dst.write(frame_syntax['end'])
					dst.write(background_syntax['end'])
				else:
					dst.write(line)
			return tex_file_name


def lyr_pdflatex(filename, options):
	texfile = filename[4:]
	print('Status: Generating pdf file ... ')
	logname = filename[:-4]+'_lyr.log'
	logfile = open(logname, 'w')
	cmd = ['pdflatex', '-interaction=nonstopmode', texfile]
	if options.debug:
		p = subprocess.Popen(cmd, cwd='out')
	else:
		p = subprocess.Popen(cmd, cwd='out', stdout=logfile)
	err = p.wait()
	if err:
		print('Error: PDF generation error, {}'.format(err))
		os._exit(1)
	logfile.flush()
	return


def lyr_clean(filename):
	texfile = filename[4:-4]
	extensions = ['.aux', '.log', '_lyr.log', '.snm', '.toc', '.nav', '.out', '.tex']
	print('Status: Cleaning tmp files ... ')
	for ext in extensions:
		cmd = ['rm', texfile+ext]
		p = subprocess.Popen(cmd, cwd='out')
		err = p.wait()
		if err:
			print('Error: Cleaning tmp files, {}'.format(err))
			os._exit(1)
	return


def lyr_resize(filename):
	texfile = filename[4:-4]+'.pdf'
	print('Status: Resizing pdf ... ')
	cmd = ['convert', '-density', '600x600', '-quality', '100', '-compress', 'jpeg', texfile, texfile]
	p = subprocess.Popen(cmd, cwd='out')
	err = p.wait()
	if err:
		print('Error: Resizing pdf file, {}'.format(err))
		os._exit(1)
	return


main()
