#!/usr/bin/python3

'lyr.py: Description of what lyr does.'

__author__      = 'Marco Torres'
__copyright__   = 'Copyright 2017, Marco Torres'


# Imports
import json
import logging
import itertools
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
blur={'init': '\\blurry{', 'mid1': '}{\\rowh*', 'mid2': '}{', 'end': '}\n'}

def main():
	# Parse input parameters
	global usage
	parser = OptionParser(usage)
	parser.add_option('-l','--list', help='List file name', type='str' )
	parser.add_option('-f','--file', help='Lyrics file name', type='str' )
	parser.add_option('-u','--unlock_caps', help='Unlock capitals for all text', action='store_true' ,default=False)
	parser.add_option('-m','--mute_pdf', help='Avoid pdf generation', action='store_true' ,default=False)
	parser.add_option('-d','--draft', help='Avoid pdf complex graphics generation', action='store_true' ,default=False)
	parser.add_option('--debug', help='Print debug messages', action='store_true' ,default=False)
	(options,args) = parser.parse_args()

	# Set logging configuration
	logging_level = logging.DEBUG if options.debug else logging.INFO
	logging.basicConfig(level=logging_level)

	# Get list
	if options.list:
		l_list = lyr_get(options.list)
		for i, song in enumerate(l_list['songs']):
			lyrics = lyr_get('lyrics/'+song+'.json')
			tex_file = lyr_format(lyrics, options, song, l_list['background'][i])
			if not options.mute_pdf:
				lyr_pdflatex(tex_file, options)
				if not options.draft:
					lyr_pdflatex(tex_file, options)
				lyr_clean(tex_file)
				lyr_resize(tex_file)
			logging.info('Process completed {}/{}'.format(i+1, len(l_list['songs'])))
		if not options.mute_pdf:
			o_list = [f +'.pdf' for f in l_list['songs']]
			lyr_merge(o_list, l_list['list_name'])
	elif options.file:
		lyrics = lyr_get(options.file)
		tex_file = lyr_format(lyrics, options, options.file[7:-5])
		if not options.mute_pdf:
			lyr_pdflatex(tex_file, options)
			if not options.draft:
				lyr_pdflatex(tex_file, options)
			lyr_clean(tex_file)
			lyr_resize(tex_file)
	else:
		logging.error('No list or file specified')
		raise

def lyr_get(file_name):

	logging.info('Parsing lyrics from {} ... '.format(file_name))
	try:
		with open(file_name) as data_file:
			try:
				lyrics = json.load(data_file)
			except Exception as err:
				logging.error('Syntax error in {}, {}.'.format(file_name, err))
				raise(err)
	except Exception as err:
		logging.error(err)
		raise(err)
	return lyrics


def lyr_format(lyrics, options, song, background=None):
	logging.info('Giving format ... ')
	song = song.replace("/", "_")
	tex_file_name = 'out/'+song+'.tex'
	copyfile('ref/template.tex', tex_file_name)
	tex_file = open(tex_file_name, 'w')

	# Get number of posible blocks per frame
	frames = []
	frame = []
	rows_per_frame = int(200 / int(lyrics['font_size']))
	logging.debug('Rows per frame = {}'.format(rows_per_frame))
	available_rows = rows_per_frame

	for block_index, block_name in enumerate(lyrics['order']):

		# Define block length
		block_len = len(lyrics[block_name])
		logging.debug('Rows of {} = {}.'.format(block_name, block_len))
		logging.debug('Available rows in frame = {}.'.format(available_rows))
		if block_len > rows_per_frame:
			# TODO: Split block
			logging.Error('Font is too large, define a smaller.')
			return

		# Allocate blocks in frames
		while True:
			if available_rows >= block_len:
				frame.append(block_name)
				available_rows -= block_len
				logging.debug('Frame = {}.'.format(frame))
				break
			else:
				frames.append(frame[:])
				frame = []
				available_rows = rows_per_frame
				logging.debug('End of frame.')

	if len(frame) != 0:
		frames.append(frame[:])
		logging.debug('End of frame.')
		logging.debug('Frames = {}.'.format(frames))

	with open('ref/template.tex') as src:
		with open(tex_file_name, 'w') as dst:
			for line in src:
				if '%lyr_font_size' in line:
					dst.write('{}{}{}'.format(font_syntax['init'],
											  lyrics['font_size'],
											  font_syntax['end']))
				elif '%lyr_text' in line:
					if not options.draft:
						background = lyrics['image'] if background is None else background
						dst.write('{}{}{}'.format(background_syntax['init'],
												  background,
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
								row = '{}{}{}{}{}{}{}'.format(blur['init'],
														row, blur['mid1'],
														(k-i-1), blur['mid2'],
														0 if options.draft else 1,
														blur['end'])
								dst.write(row)
							dst.write(tikz_syntax['end'])
							dst.write(block_syntax['end'])
						dst.write(frame_syntax['end'])
					if not options.draft:
						dst.write(background_syntax['end'])
				else:
					dst.write(line)
			return tex_file_name


def lyr_pdflatex(filename, options):
	texfile = filename[4:]
	logging.info('Generating pdf file ... ')
	logname = filename[:-4]+'_lyr.log'
	logfile = open(logname, 'w')
	cmd = ['pdflatex', '-interaction=nonstopmode', texfile]
	stdout = None if options.debug else logfile
	p = subprocess.Popen(cmd, cwd='out', stdout=stdout)
	err = p.wait()
	if err:
		logging.error('PDF generation error, {}'.format(err))
		raise(err)
	logfile.flush()
	return


def lyr_clean(filename):
	texfile = filename[4:-4]
	extensions = ['.aux', '.log', '_lyr.log', '.snm', '.toc', '.nav', '.out', '.tex']
	logging.info('Cleaning tmp files ... ')
	for ext in extensions:
		cmd = ['rm', texfile+ext]
		p = subprocess.Popen(cmd, cwd='out')
		err = p.wait()
		if err:
			logging.error('Cleaning tmp files, {}'.format(err))
			raise(err)
	return


def lyr_resize(filename):
	texfile = filename[4:-4]+'.pdf'
	logging.info('Resizing pdf ... ')
	cmd = ['convert', '-density', '600x600', '-quality', '100', '-compress', 'jpeg', texfile, texfile]
	p = subprocess.Popen(cmd, cwd='out')
	err = p.wait()
	if err:
		logging.error('Resizing pdf file, {}'.format(err))
		raise(err)
	return


def lyr_merge(file_list, file_name):
	logging.info('Merging pdfs ... ')
	file_name += '.pdf'
	file_list = ['out/'+song.replace("/", "_") for song in file_list]
	cmd = ['pdftk', file_list, 'cat', 'output', file_name]
	cmd = [([x] if isinstance(x,str) else x) for x in cmd]
	cmd = list(itertools.chain(*cmd))
	p = subprocess.Popen(cmd)
	err = p.wait()
	if err:
		logging.error('Merging pdfs, {}'.format(err))
		raise(err)
	return


main()
