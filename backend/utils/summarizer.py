def generate_summary(text, sentence_count=3):
    from sumy.parsers.plaintext import PlaintextParser
    from sumy.nlp.tokenizers import Tokenizer
    from sumy.summarizers.text_rank import TextRankSummarizer

    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = TextRankSummarizer()

    summary_sentences = summarizer(parser.document, sentence_count)

    # ✅ Filter short/useless sentences
    final_summary = []
    for sentence in summary_sentences:
        if len(str(sentence).split()) > 8:   # keep meaningful sentences
            final_summary.append(str(sentence))

    return " ".join(final_summary)