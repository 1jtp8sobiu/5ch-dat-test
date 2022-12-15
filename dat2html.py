#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import glob
import getopt
import re
import unicodedata
import logging
import gzip

VERSION = "0.5.0"


class Dat2Html:
    def __init__(self, template_dir=None):
        self.set_template_dir(template_dir)

    def set_template_dir(self, template_dir):
        self.template_dir = template_dir
        self.template_header = self.get_template_header()
        self.template_body = self.get_template_body()
        self.template_footer = self.get_template_footer()

    def convert(self, lines, filename_noext):
        output = ""
        try:
            title = get_title(lines[0])
        except IndexError:
            return None
        count = len(lines)
        filesize = len("".join(lines))

        params = {
            "title": title,
            "filename": filename_noext,
            "count": count,
            "link_all": self.get_link_all(filename_noext),
            "link_last50": self.get_link_last50(count, self.template_dir),
            "link_pager": self.get_link_pager(count, self.template_dir),
            "skin_path": self.get_skin_path(),
            "filesize": filesize,
            "filesize2": filesize / 1024,
        }

        anker_count = self.get_anker_count(lines)
        id_count = self.get_id_count(lines)
        output += self.template_header % params
        number = 1
        for line in lines:
            try:
                name, email, date, message = line.split("<>")[:4]
            except ValueError:
                return None

            if "ID:" in date:
                id = date.split("ID:")[1]
            else:
                id = ""

            if self.template_dir == "*text*":
                message = self.html2text(message)
            else:
                message = self.auto_link(message, self.template_dir)

            prefix = ""
            if not self.template_dir:
                prefix = "R"
            if number in anker_count:
                tmp = []
                for num in anker_count[number]:
                    tmp.append(f'<a href="#{prefix}{num}">{num}</a>') 
                anker_str = ", ".join(tmp)
                anker_str = '<font size="2">(' + anker_str + ')</font>'
                message = anker_str + "<br>" + message

            name2 = "<font color=green><b>%s</b></font>" % name
            if email != "":
                name2 = '<font color=blue><b>%s</b></font><font size="2"> %s</font>' % (name, email)
            if self.template_dir == "*text*":
                name2 = "%s" % name
            if self.template_dir == "*text*" and email != "":
                name2 = ("%s E-mail:%s" %
                         (name.replace("<b>", "").replace("</b>", ""), email))
            if id in id_count:
                if id_count[id] >= 10:
                    date += f'<font size="2" color="red"> {id_count[id]}回</font>'
                elif id_count[id] >= 5:
                    date += f'<font size="2" color="#FF0099"> {id_count[id]}回</font>'
                elif id_count[id] > 1:
                    date += f'<font size="2"> {id_count[id]}回</font>'

            output += (self.template_body %
                       {"number": number, "name": name, "email": email,
                        "name2": name2, "date": date, "message": message})
            number += 1

        output += self.template_footer % params
        return output

    def convert_file(self, input_file, output_dir):
        filename_noext = re.sub("\.dat\.gz$|\.dat$", "",
                                os.path.basename(input_file))
        try:
            lines = open_file(input_file).readlines()
            output = self.convert(lines, filename_noext)
            if output is None:
                logging.error("Could not parse file: %s" % input_file)
                return False
        except UnicodeDecodeError:
            logging.error("cannot decode %s, skip." % input_file)
            return False

        output_file = os.path.join(output_dir, filename_noext + ".html")
        if self.template_dir == "*text*":
            output_file = os.path.join(output_dir, filename_noext + ".txt")
        if os.path.exists(output_file):
            logging.warning("%s already exists. Overwriting ..." %
                            output_file)

        logging.info("Generating %s" % output_file)
        try:
            if output_dir == "-":
                output_file = "stdout"
                sys.stdout.write(output)
            else:
                f = open(output_file, "w", newline="\n", encoding="utf-8")
                f.write(output)
                f.close()
        except:
            logging.error("Failed to write file: %s" % output_file)
            return False

        return True

    def convert_files(self, input_files, output_dir,
                      index='index.html', subject=False):
        filenames = get_filenames(input_files)

        if len(filenames) <= 0:
            logging.error("No input files")
            sys.exit(2)

        if output_dir != "-" and not os.path.exists(output_dir):
            logging.info("Creating directory ...")
            try:
                os.makedirs(output_dir)
            except OSError as xxx_todo_changeme:
                (errorno, strerror) = xxx_todo_changeme.args
                logging.error("Could not create %s: %s" %
                              (output_dir, strerror))
                sys.exit(2)
        if output_dir != "-" and not os.access(output_dir, os.W_OK):
            logging.error("Could not open %s: permission denied" % output_dir)
            sys.exit(2)

        for filename in filenames:
            self.convert_file(filename, output_dir)

        if index:
            make_index(input_files=filenames, index=index)
        if subject:
            make_subject(filenames, output_dir)

    def template_exists(self):
        if self.template_dir is None:
            return False

        found = True
        filenames = ["header.html", "footer.html", "res.html"]
        for filename in filenames:
            found &= (
                os.path.exists(os.path.join(self.template_dir, filename)) or
                os.path.exists(
                    os.path.join(self.template_dir, filename.capitalize())))
        return found

    def read_template(self, filename):
        if (os.path.exists(os.path.join(self.template_dir,
                                        filename.capitalize()))):
            filename = filename.capitalize()
        logging.info("%s exists. Loading ..." %
                     os.path.join(self.template_dir, filename))
        s = open(os.path.join(self.template_dir, filename), encoding="cp932").read()
        return s

    def get_template_header(self):
        if self.template_dir == "*text*":
            s = "%(title)s\n\n"
        elif self.template_exists():
            s = self.read_template("header.html")
            s = s.replace("<THREADNAME/>", "%(title)s")
            s = s.replace("<THREADURL/>", "")
            s = s.replace("<SKINPATH/>", "%(skin_path)s")
            s = s.replace("<GETRESCOUNT/>", "%(count)s")
            s = s.replace("<LINK_BACKTOINDEX/>", "")
            s = s.replace("<LINK_BACKTOBOARD/>", "")
            s = s.replace("<LINK_SOURCETHREAD/>", "")
            s = s.replace("<LINK_ALL/>", "%(link_all)s")
            s = s.replace("<LINK_RESNUMBER/>", "%(link_pager)s")
            s = s.replace("<LINK_LASTFIFTY/>", "%(link_last50)s")
        else:
            s = "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.01 Transitional//EN\">\n"
            s += "<html>\n"
            s += "<head>\n" 
            s += get_gtag_code()
            s += "<meta http-equiv=\"Content-Type\" content=\"text/html\"><meta name=\"Author\" content=\"%(filename)s\">\n"
            s += "<title>%(title)s</title>\n"
            s += "</head>\n"
            s += "<body bgcolor=#efefef text=black link=blue alink=red vlink=#660099>\n"
            s += "<div style=\"margin-top:1em;\"><span style='float:left;'>\n"
            s += "%(link_all)s %(link_pager)s %(link_last50)s\n"
            s += "</span>&nbsp;</div>\n"
            s += "<hr style=\"background-color:#888;color:#888;border-width:0;height:1px;position:relative;top:-.4em;\">\n"
            s += "<h1 style=\"color:red;font-size:larger;font-weight:normal;margin:-.5em 0 0;\">%(title)s</h1>\n"
            s += "<dl class=\"thread\">\n"
        return s

    def get_template_body(self):
        if self.template_dir == "*text*":
            s = "%(number)s 名前：%(name2)s ：%(date)s\n" \
                "%(message)s\n\n"
        elif self.template_exists():
            s = self.read_template("res.html")
            s = s.replace("<NUMBER/>", "<a href=\"menu\:%(number)s\" "
                          "name=\"%(number)s\">%(number)s</a>")
            s = s.replace("<PLAINNUMBER/>", "%(number)s")
            s = s.replace("<NAME/>", "<b>%(name)s</b>")
            s = s.replace("<MAIL/>", "%(email)s")
            s = s.replace("<MAILNAME/>", "%(name2)s")
            s = s.replace("<DATE/>", "%(date)s")
            s = s.replace("<MESSAGE/>", "%(message)s")
        else:
            s = "<dt><a name=\"R%(number)s\">%(number)s</a> " \
                "名前：%(name2)s：" \
                "%(date)s<dd>%(message)s<br><br>\n"
        return s

    def get_template_footer(self):
        if self.template_dir == "*text*":
            s = ""
        elif self.template_exists():
            s = self.read_template("footer.html")
            s = s.replace("<LINK_BACKTOINDEX/>", "")
            s = s.replace("<LINK_ALL/>", "%(link_all)s")
            s = s.replace("<LINK_BACK/>", "").replace("<LINK_NEXT/>", "")
            s = s.replace("<LINK_LASTFIFTY/>", "%(link_last50)s")
            s = s.replace("<LINK_CREDIT/>", "")
            s = s.replace("<INDEXCODE_FORRECOMPOSE/>", "")
            s = s.replace("<SIZEKB/>", "%(filesize2)s")
            s = s.replace("<SIZE/>", "%(filesize)s")
            s = s.replace("<BBSNAME/>", "").replace("<BOARDNAME/>", "")
            s = s.replace("<BOARDURL/>", "")
        else:
            s = "</dl>\n" \
                "<hr>\n" \
                "%(link_all)s\n" \
                " %(link_last50)s\n" \
                "</body>\n" \
                "</html>\n"
        return s

    def html2text(self, message):
        p = re.compile(
            r'<a href="../test/read.cgi/\w+/\d+/\d+[-,]?[^\"]*" '
            r'target="_blank">([^<]+)</a>')
        message = p.sub(r'\1', message)

        message = re.compile(r'<br>').sub("\n", message)
        message = re.compile(r' ?\n ?').sub("\n", message)
        message = re.compile(r'^([^ ])').sub(r' \1', message)
        message = re.compile(r'^ ').sub("      ", message)
        message = re.compile(r' $').sub("", message)
        message = re.compile('\n').sub("\n      ", message)
        message = message.replace("&lt;", "<").replace("&gt;", ">")
        message = message.replace("&nbsp;", " ").replace("&quot;", "\"")
        message = message.replace("&amp;", "&")

        return message

    def auto_link(self, message, use_template=False):
        prefix = ""
        if not use_template:
            prefix = "R"

        p = re.compile(
            r'<a href="../test/read.cgi/\w+/\d+/\d+[-,]?[^\"]*" '
            r'target="_blank">([^<]+)</a>')
        message = p.sub(r'\1', message)

        p = re.compile(
            '((?:&gt;|＞){1,2})(\\d+)((?:[^&][-,\\d]+)?)')
        message = p.sub(r'<a href="#%(prefix)s\2">\1\2\3</a>', message)
        message = message.replace("%(prefix)s", prefix)

        p = re.compile(
            '((?:&gt;|＞){1,2})((?:\\x82[\\x4F-\\x58])+)')
        message = p.sub(
            lambda x: '<a href="#%s%s">%s%s</a>' %
            (prefix, unicodedata.normalize("NFKC", x.group(2))
             , x.group(1), x.group(2)), message)

        p = re.compile(r'([^\"h]|^)(h?ttps?|ftp)(://[\w:;/.?%\#&=+-~!*@$]+)')
        correct_scheme = lambda x: 'http' if x == 'ttp' else \
                                  ('https' if x == 'ttps' else x)
        message = p.sub(
            lambda x: '%(before)s<a href="%(scheme)s%(body)s" rel="noopener noreferrer" target="_blank">'
            '%(raw_scheme)s%(body)s</a>' %
            {'before': x.group(1), 'raw_scheme': x.group(2),
             'body': x.group(3), 'scheme': correct_scheme(x.group(2))},
            message)

        return message

    def get_anker_count(self, lines):
        anker_count = {}
        for i, line in enumerate(lines, 1):
            ankers = re.findall(r'&gt;&gt;[0-9]{1,3}', line)
            for anker in ankers:
                anker_target = int(anker.replace('&gt;&gt;', ''))
                if anker_target in anker_count:
                    if i not in anker_count[anker_target]:
                        anker_count[anker_target].append(i)
                else:
                    anker_count[anker_target] = [i]
        return anker_count

    def get_id_count(self, lines):
        id_count = {}
        for line in lines:
            try:
                id = line.split('<>')[2].split('ID:')[1]
            except IndexError:
                continue

            if id in id_count:
                id_count[id] += 1
            else:
                id_count[id] = 1
        return id_count

    def get_skin_path(self):
        skin_path = ""
        if self.template_dir:
            skin_path = "file://" + os.path.abspath(self.template_dir) + "/"
        return skin_path

    def get_link_all(self, filename_noext):
        return '<a href="%s.html">全部</a>' % filename_noext

    def get_link_last50(self, count, use_template=False):
        last50 = count - 49
        if last50 <= 0:
            last50 = 1
        prefix = ""
        if not use_template:
            prefix = "R"
        return ('<a href="#%s%s">最新50</a>' %
                (prefix, last50))

    def get_link_pager(self, count, use_template=False):
        link_pager = ""
        prefix = ""
        if not use_template:
            prefix = "R"
        for i in range(0, round(count / 100 + 1)):
            link_pager += ('<a href="#%s%s">%s-</a> ' %
                           (prefix, i * 100 + 1, i * 100 + 1))
        link_pager = link_pager.rstrip()
        return link_pager


def convert(lines, filename_noext, template_dir=None):
    dat2html = Dat2Html(template_dir)
    output = dat2html.convert(lines, filename_noext)
    return output


def convert_file(input_file, output_dir, template_dir=None):
    dat2html = Dat2Html(template_dir)
    return dat2html.convert_file(input_file, output_dir)


def convert_files(input_files, output_dir, template_dir=None,
                  index="index.html", subject=False):
    dat2html = Dat2Html(template_dir)
    return dat2html.convert_files(input_files=input_files, output_dir=output_dir, index=index, subject=subject)


def get_filenames(input_files):
    filenames = []
    for pathname in input_files:
        logging.debug("get_filenames(): pathname=%s" % pathname)
        if os.path.isdir(pathname):
            filenames += get_filenames(
                glob.glob(os.path.abspath(pathname) + "/*.dat") +
                glob.glob(os.path.abspath(pathname) + "/*.dat.gz"))
            continue
        if not os.path.isfile(pathname):
            logging.warning("Skipping %s: not found" % pathname)
            continue
        if not os.access(pathname, os.R_OK):
            logging.warning("Skipping %s: permission denied" % pathname)
            continue
        filenames.append(pathname)

    sort_nicely(filenames)
    return filenames


def sort_nicely(l):
    """ Sort the given list in the way that humans expect.
    """
    convert = lambda text: int(text) if text.isdigit() else text
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return l.sort(key=alphanum_key)


def open_file(filename):
    if filename.endswith(".gz"):
        return gzip.open(filename, encoding="cp932", errors="ignore")
    return open(filename, encoding="cp932", errors="ignore")


def make_index(input_files, index):
    index_file = index
    if os.path.exists(index_file):
        logging.info("%s already exists. Adding new threads ..." % index_file)
        with open(index_file, encoding='utf-8') as f:
            existing_threads = f.read().split('<div style="margin-bottom:1em;">\n')[1].split('</div>')[0]
            existing_threads = existing_threads.splitlines()
    else:
        existing_threads = []
    
    index_title = index_file.replace(".html", "")
    output = "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.01 Transitional//EN\">\n"
    output += "<html>\n"
    output += "<head>\n"
    output += get_gtag_code()
    output += "<meta http-equiv=\"Content-Type\" content=\"text/html><meta http-equiv=\"Content-Style-Type\" content=\"text/css\">\n"
    output += f"<title>{index_title}</title>\n"
    output += "</head>\n"
    output += "<body bgcolor=\"#efefef\" text=\"black\" link=\"blue\" alink=\"red\" vlink=\"#660099\">\n"
    output += "<div style=\"margin-bottom:0.5em;\"></div>\n"
    output += "<div style=\"margin-bottom:1em;\">\n"

    number = 1
    for filename in input_files:
        try:
            first_line = open_file(filename).readline()
            title = get_title(first_line)
            date_time = get_date_time(first_line)
            dat_path = os.path.basename(filename)
            html_path = os.path.basename(filename).replace(".dat", ".html")
            count = len(open_file(filename).readlines())
            
            for i, line in enumerate(existing_threads):
                if html_path in line:
                    existing_threads[i] = (" %s / <a href=\"html/%s\">html</a> / <a href=\"dat/%s\">dat</a> / %s(%s)<br>"
                                            % (date_time, html_path, dat_path, title, count))
                    break
            else:
                existing_threads.append(" %s / <a href=\"html/%s\">html</a> / <a href=\"dat/%s\">dat</a> / %s(%s)<br>"
                                        % (date_time, html_path, dat_path, title, count))
            number += 1
        except UnicodeDecodeError:
            logging.warning("UnicodeDecodeError %s ..." % filename)
            continue
    
    existing_threads.sort(reverse=True)
    output += "\n".join(existing_threads) + "\n"
    output += "</div>\n</body>\n</html>\n"

    logging.info("Generating %s" % index_file)
    try:
        f = open(index_file, "w", newline="\n", encoding="utf-8")
        f.write(output)
        f.close()
    except IOError as xxx_todo_changeme1:
        (errorno, strerror) = xxx_todo_changeme1.args
        logging.error("Failed to write %s: %s" % (index_file, strerror))
        return False

    return True


def make_subject(input_files, output_dir):
    subject_file = os.path.join(output_dir, "subject.txt")
    if os.path.exists(subject_file):
        logging.warning("%s already exists. Overwriting ..." % subject_file)

    logging.info("Generating %s" % subject_file)
    output = ""
    for filename in input_files:
        title = get_title(open_file(filename).readline())
        count = len(open_file(filename).readlines())
        output += ("%s<>%s (%s)\n" %
                   (os.path.basename(filename), title, count))

    try:
        if output_dir == "-":
            subject_file = "stdout"
            sys.stdout.write(output)
        else:
            f = open(subject_file, "w")
            f.write(output)
            f.close()
    except IOError as xxx_todo_changeme2:
        (errorno, strerror) = xxx_todo_changeme2.args
        logging.error("Failed to write %s: %s" % (subject_file, strerror))
        return False

    return True


def get_gtag_code():
    try:
        with open('code.txt') as f:
            return f.read()
    except FileNotFoundError:
        return ''


def get_title(line):
    try:
        title = line.split("<>")[4].rstrip("\n")
    except IndexError:
        logging.warning("Could not get title")
        return "(Untitled)"
    return title


def get_date_time(line):
    try:
        date_time = line.split("<>")[2]
    except IndexError:
        logging.warning("Could not get datetime")
        return ""
    return date_time[0:22]


def auto_link(message, use_template=False):
    dat2html = Dat2Html()
    return dat2html.auto_link(message, use_template)


def html2text(message):
    dat2html = Dat2Html()
    return dat2html.html2text(message)


def template_exists(template_dir):
    dat2html = Dat2Html(template_dir)
    return dat2html.template_exists()


def print_help():
    print("Usage: dat2html [OPTIONS...] [PATH...]\n")
    print("Options:")
    print("  --template        specify the template directory")
    print("  -o, --output      specify the output directory")
    print("  --text            convert to text format instead of HTML")
    print("  --index           generate an index file (specify the filename)")
    print("  --subject         generate a subject.txt file")
    print("  -q, --quiet       suppress warning and info messages")
    print("  -v, --verbose     print debugging messages")
    print("  -h, --help        display this help and exit")
    print("  -V, --version     display version information and exit")


def print_version():
    print("dat2html (dat2html-gtk) %s" % VERSION)


def main():
    template_dir = None
    output_dir = os.getcwd()
    index = "index.html"
    subject = False
    log_level = logging.INFO

    try:
        opts, args = getopt.getopt(
            sys.argv[1:],
            "o:qhvV",
            ["template=", "output=", "text", "index=", "subject",
             "quiet", "verbose", "help", "version"])
    except getopt.GetoptError:
        print_help()
        sys.exit(2)

    for opt, value in opts:
        if opt == "--template":
            template_dir = value
        if opt in ("-o", "--output"):
            output_dir = value
        if opt == "--text":
            template_dir = "*text*"
        if opt == "--index":
            index = value
        if opt == "--subject":
            subject = True
        if opt in ("-q", "--quiet"):
            log_level = logging.ERROR
        if opt in ("-v", "--verbose"):
            log_level = logging.DEBUG
        if opt in ("-h", "--help"):
            print_help()
            sys.exit()
        if opt in ("-V", "--version"):
            print_version()
            sys.exit()
        if template_dir == "*text*":
            index = False

    if not len(args):
        print_help()
        sys.exit(2)

    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    if "-" in args:
        if len(args) > 1:
            logging.error("Too many arguments")
            sys.exit(2)
        output = convert(sys.stdin.readlines(), "%(filename)s", template_dir)
        print(output, end=' ')
    else:
        convert_files(args, output_dir=output_dir, template_dir=template_dir, index=index, subject=subject)


if __name__ == "__main__":
    main()
