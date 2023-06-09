import re


questions = """
Who killed izuna Uchiha?
A.	Tobirama
B.	Hashirama
C.	Tachibana
D.	Itachi

"""


def main():
    replaced = re.sub(r"[A-Z]\.", "||", questions)
    print(replaced.replace("\n", "").replace("\t", ""))


if __name__ == "__main__":
    main()
