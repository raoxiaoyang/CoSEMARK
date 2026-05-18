# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from bleu import _bleu


def normalize_lang(lang):
    aliases = {
        "cs": "c_sharp",
        "c#": "c_sharp",
        "csharp": "c_sharp",
        "c_sharp": "c_sharp",
        "cpp": "cpp",
        "c++": "cpp",
        "java": "java",
        "javascript": "javascript",
        "js": "javascript",
        "python": "python",
        "py": "python",
        "php": "php",
        "go": "go",
        "golang": "go",
        "ruby": "ruby",
    }
    normalized = aliases.get(lang.strip().lower())
    if normalized is None:
        raise ValueError(f"Unsupported language alias for CodeBLEU: {lang}")
    return normalized


def try_compute_codebleu(refs, pres, lang):
    if not refs:
        return 0.0, None

    try:
        from codebleu import calc_codebleu
    except ImportError as exc:
        return None, (
            "CodeBLEU dependency is not installed. Install the `codebleu` "
            f"package to enable this metric. ({exc!r})"
        )

    references = [[ref] for ref in refs]
    try:
        result = calc_codebleu(references, pres, lang=lang)
    except TypeError:
        # Older implementations may expect a flat reference list.
        result = calc_codebleu(refs, pres, lang=lang)

    score = result.get("codebleu")
    if score is None:
        raise ValueError(f"Unexpected CodeBLEU result: {result}")
    return round(100 * score, 2), None


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Evaluate code translation predictions.')
    parser.add_argument('--references', '-ref', help="filename of the labels, in txt format.")
    parser.add_argument('--predictions', '-pre', help="filename of the leaderboard predictions, in txt format.")
    parser.add_argument(
        "--lang",
        default="c_sharp",
        help="Target programming language for CodeBLEU, e.g. c_sharp, java, python.",
    )
    parser.add_argument(
        "--strict-codebleu",
        action="store_true",
        help="Fail when CodeBLEU cannot be computed.",
    )

    args = parser.parse_args()
    args.lang = normalize_lang(args.lang)

    refs = [x.strip() for x in open(args.references, 'r', encoding='utf-8').readlines()]
    pres = [x.strip() for x in open(args.predictions, 'r', encoding='utf-8').readlines()]

    assert len(refs) == len(pres)

    length = len(refs)
    count = 0
    for i in range(length):
        r = refs[i]
        if i==0:
            print(r)
        p = pres[i]
        if i==0:
            print(p)
        if r == p:
            count += 1
    acc = round(count/length*100, 2)

    bleu_score = round(_bleu(args.references, args.predictions),2)
    codebleu_score, codebleu_error = try_compute_codebleu(refs, pres, args.lang)

    if codebleu_error is not None:
        if args.strict_codebleu:
            raise RuntimeError(codebleu_error)
        print('BLEU:',  bleu_score, '; CodeBLEU: unavailable', '; Acc:', acc)
        print('CodeBLEU error:', codebleu_error)
    else:
        print('BLEU:',  bleu_score, '; CodeBLEU:', codebleu_score, '; Acc:', acc)

if __name__ == '__main__':
    main()
