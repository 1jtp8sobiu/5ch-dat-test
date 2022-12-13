import pathlib
import os
import shutil
import time
import datetime
import sys
import subprocess

DAT_KAKOLOG_DATA = 'dat_kakolog.txt'
CHECK_INTERVEL = 3600

def git_push():
    print('git push...')
    cmd = ['git', 'add', '.']
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(proc.stdout.decode('utf8'))

    cmd = ['git', 'commit', '-a', '-m', 'Update']
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(proc.stdout.decode('utf8'))

    cmd = ['git', 'push', 'origin', 'master']
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(proc.stdout.decode('utf8'))
    print('git_push done...')


def dat_2_html(path, dats):
    # datを年-月ごとに区切る
    dat_months = {}
    for dat in dats:
        dat_id = dat.split('/')[-1].split('.')[0]
        dat_datetime = datetime.datetime.fromtimestamp(int(dat_id))
        dat_month = str(dat_datetime)[0:7]
        if dat_month not in dat_months:
            dat_months[dat_month] = [dat]
        else:
            dat_months[dat_month].append(dat)
    print(dat_months)

    for k, v in dat_months.items():
        sys.argv = ['',]
        sys.argv.append('--index')
        sys.argv.append(f'{path}/{k}.html')
        sys.argv.append('--output')
        sys.argv.append(f'{path}/html')
        sys.argv += v
        import dat2html
        dat2html.main()


def make_root_index(path):
    htmls = list(pathlib.Path(path).glob('*.html'))
    htmls.sort(reverse=True)

    output = "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.01 " \
        "Transitional//EN\">\n" \
        "<html>\n" \
        "<head>\n" \
        "<meta http-equiv=\"Content-Type\" content=\"text/html>" \
        "<meta http-equiv=\"Content-Style-Type\" content=\"text/css\">\n" \
        f"<title>{path}</title>\n" \
        "</head>\n" \
        "<body bgcolor=\"#efefef\" text=\"black\" link=\"blue\" " \
        "alink=\"red\" vlink=\"#660099\">\n" \
        "<div style=\"margin-bottom:0.5em;\"></div>\n" \
        "<div style=\"margin-bottom:1em;\">\n"

    for html in htmls:
        if html.name == 'index.html':
            continue
        output += f'<a href="{html.name}">{html.stem}</a><br>\n'

    output += "</div>\n</body>\n</html>\n"
    print('Generating root index file')
    with open(f'{path}/index.html', mode='w', encoding='utf-8', newline='\n') as f:
        f.write(output)


def load_dat_kakolog_data(path):
    if not os.path.isfile(f'{path}/{DAT_KAKOLOG_DATA}'):
        return set()
    else:
        with open(f'{path}/{DAT_KAKOLOG_DATA}') as f:
            ids = f.read().splitlines()
        return set(ids)


def save_dat_kakolog_data(path, obj):
    with open(f'{path}/{DAT_KAKOLOG_DATA}', mode='w') as f:
        obj = list(obj)
        obj.sort()
        f.write('\n'.join(obj))


def main():
    while True:
        with open('boards.txt') as f:
            check_boards = f.read().splitlines()
            
        for check_board in check_boards:
            os.makedirs(f'{check_board}/dat', exist_ok=True)
            os.makedirs(f'{check_board}/html', exist_ok=True)
            
            copy_src = 'X:/python_tools/5ch_scrape'
            copy_dst = f'{check_board}/dat'
    
            board_name = check_board.split('/')[1]
            server = check_board.split('/')[0].split('.')[0]
    
            start = time.perf_counter()
            dats_on_s = pathlib.Path(copy_src).glob(f'{server}_{board_name}_*.dat')
            dats_on_s = list(dats_on_s)
            dats_on_s.sort()
            print(time.perf_counter() - start)
    
            # copy dat from the server to local
            count = 0
            added_dats = []
            dat_kakolog_data = load_dat_kakolog_data(check_board)
            for dat_on_s in dats_on_s:
                dat_id = dat_on_s.stem.split('_')[-1]
                
                if dat_id.startswith('9'):
                    continue
                if dat_id in dat_kakolog_data:
                    continue
    
                dat_on_s_info = os.stat(dat_on_s)
                dat_on_s_lastmod = dat_on_s_info.st_mtime
    
                if time.time() - dat_on_s_lastmod > CHECK_INTERVEL:
                    dat_kakolog_data.add(dat_id)
                    print(datetime.datetime.fromtimestamp(int(dat_on_s_lastmod)))
    
                    dat_on_l = f'{check_board}/dat/{dat_id}.dat'
                    shutil.copy2(dat_on_s, dat_on_l)
                    added_dats.append(dat_on_l)
                    count += 1
                    if count == 200:
                        save_dat_kakolog_data(check_board, dat_kakolog_data)
                        dat_2_html(check_board, added_dats)
                        make_root_index(check_board)
                        git_push()
                        count = 0
                        added_dats = []
                        print('wating 600')
                        time.sleep(600)
            save_dat_kakolog_data(check_board, dat_kakolog_data)
            dat_2_html(check_board, added_dats)
            make_root_index(check_board)
            git_push()
            print('wating', CHECK_INTERVEL)
            time.sleep(CHECK_INTERVEL)


if __name__ == "__main__":
    main()
