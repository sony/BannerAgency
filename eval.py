import os, argparse
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from tools.tool_utils import prepare_image_message, BOutput
from dotenv import load_dotenv
load_dotenv()

parser = argparse.ArgumentParser()
parser.add_argument("--evaluator", type=str, help="gpt5nano or claude", default="gpt5nano")
parser.add_argument("--metric", type=str, help="alignment, overlap, whitespace, qa", default="CPYQ")
parser.add_argument("--image_file" , type=str, help="Path to the image to be evaluated")
parser.add_argument("--logo_file", type=str, help="Path to the logo")
parser.add_argument("--banner_request", type=str, help="The banner request")

args = parser.parse_args()

if args.evaluator == "gpt5nano":
    llm = ChatOpenAI(
        model="gpt-5-nano",  # GPT-5-nano model
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        temperature=1, 
        max_tokens=2000,
        max_retries=2,
    )
elif args.evaluator == "claude":
    llm = ChatAnthropic(
        model="claude-3-5-sonnet-20241022",  # or another Claude model version
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        temperature=0.3,
        max_tokens=200,  # or specify a limit
        max_retries=2
    )

TAA ="""Definition: Measures how well the generated banner ad aligns with the given request, including the theme, target audience, and primary purpose.

Instructions for Scoring:
5 – Perfectly aligns with the request (theme, audience, purpose are all clearly reflected).
4 – Mostly aligns, but minor details could be improved.
3 – Somewhat aligns, but key elements are missing or unclear.
2 – Barely aligns, with major missing or incorrect elements.
1 – Does not align with the request at all.

Justification Required: Explain how well the banner captures the requested theme and audience.
"""

LPS="""Definition: Evaluates whether the logo is well-integrated into the design in terms of visibility, size, and positioning.

Instructions for Scoring:
5 – Logo is well-placed, clearly visible, proportionate, and blends seamlessly.
4 – Logo is well-placed but could be slightly improved (e.g., minor size or position adjustments).
3 – Logo is visible but not ideally placed (e.g., too small, too large, or slightly obstructed).
2 – Logo placement is poor (e.g., difficult to notice, awkward positioning).
1 – Logo is either missing or completely misplaced.

Justification Required: Explain how the logo is positioned and whether it contributes to brand identity.
"""

AQS="""Definition: Measures the visual appeal, including color harmony, layout balance, typography, and overall design quality.

Instructions for Scoring:
5 – Visually outstanding, professional design, well-balanced, with harmonious colors and readable text.
4 – Well-designed, but small refinements could enhance it.
3 – Acceptable but has notable design flaws (e.g., poor contrast, unbalanced elements).
2 – Visually weak, with noticeable design mistakes.
1 – Poor design, lacks professionalism or coherence.

Justification Required: Explain what makes the design appealing or unappealing.
"""

CTAE="""Definition: Evaluates whether the Call-to-Action (CTA) is clear, engaging, and visually emphasized.

Instructions for Scoring:
5 – CTA is clear, compelling, well-placed, and visually prominent.
4 – CTA is effective but could be slightly improved (e.g., contrast, size).
3 – CTA is present but lacks emphasis or clarity.
2 – CTA is weak, hard to notice, or poorly worded.
1 – No clear CTA is present.

Justification Required: Explain how effective the CTA is in prompting user action.
"""

CPYQ="""Definition: Evaluates the effectiveness of the headline, subheadline, and any other text in the banner ad, focusing on clarity, readability, persuasiveness, and grammatical correctness.

Instructions for Scoring:
5 – Copy is clear, engaging, grammatically correct, and persuasive, making the message effective.
4 – Copy is well-written but could be slightly improved (e.g., minor word choice refinements).
3 – Copy is somewhat effective but has issues in clarity, grammar, or persuasiveness.
2 – Copy is weak, hard to read, contains noticeable grammatical mistakes, or lacks impact.
1 – Copy is unclear, irrelevant, or difficult to read due to poor design or bad wording.

Justification Required:
Is the copy easy to read against the background?
Does it match the banner’s purpose and target audience?
Is it persuasive and action-driven?
Are there any grammatical or spelling errors?
"""

BIS="""Definition: Measures how well the banner ad visually and stylistically aligns with the brand’s identity beyond just logo placement. This includes color consistency, typography, imagery, and overall brand feel.

Instructions for Scoring:
5 – Strong brand consistency; the banner design aligns well with the provided logo and conveys a recognizable brand identity.
4 – Mostly aligns, but minor refinements could improve brand consistency.
3 – Somewhat aligns, but noticeable inconsistencies exist (e.g., off-brand colors, incorrect typography).
2 – Weak brand alignment, only the logo represents the brand while other design choices feel unrelated.
1 – No brand identity is reflected; the banner appears generic or disconnected from the brand.

Justification Required:
Are the colors and typography in line with the brand’s usual style?
Does the imagery and layout reinforce the brand’s visual identity?
Does the overall aesthetic feel like it belongs to the brand, or does it look generic?
"""

BANNER_AD_REPORT_PROMPT = """You are an expert in advertising design, marketing, and visual communication. Your task is to evaluate a banner ad image based on the following principle given the advertiser's logo and banner request. You should rate on a scale of 1 to 5, where 1 is poor and 5 is excellent. You should also provide a brief justification for your score.

{score_princple}

Please start evaluating the banner ad image. Output your answer in the format of {{"score": , "explanation": "explain concisely why you gave this score"}}
"""

if args.metric == "TAA":
    system_prompt = BANNER_AD_REPORT_PROMPT.format(score_princple=TAA)
elif args.metric == "LPS":
    system_prompt = BANNER_AD_REPORT_PROMPT.format(score_princple=LPS)
elif args.metric == "AQS":  
    system_prompt = BANNER_AD_REPORT_PROMPT.format(score_princple=AQS)
elif args.metric == "CTAE":
    system_prompt = BANNER_AD_REPORT_PROMPT.format(score_princple=CTAE)
elif args.metric == "CPYQ":
    system_prompt = BANNER_AD_REPORT_PROMPT.format(score_princple=CPYQ)
elif args.metric == "BIS":
    system_prompt = BANNER_AD_REPORT_PROMPT.format(score_princple=BIS)
print(system_prompt)

def run(image_path, logo_path, banner_request):
    print(f"Processing {image_path}")
    print(f"Processing {logo_path}")
    print(banner_request)
    if not os.path.isfile(image_path):
        print(f"error: Skipping {image_path}")
        exit(4)
    if not os.path.isfile(logo_path):
        print(f"error: Skipping {image_path}")
        exit(4)
    image_data = prepare_image_message(image_path)
    logo_data = prepare_image_message(logo_path)
    planning_messages = [
        SystemMessage(content=system_prompt),
    HumanMessage(content=[
        {
            "type": "text", 
            "text": "The banner image to be evaluated is:"
        },
        {
            "type": "image_url",
            "image_url": {
                "url": image_data
            }
        },
        {
            "type": "text", 
            "text": "For your reference, the advertiser logo is:"
        },
        {
            "type": "image_url",
            "image_url": {
                "url": logo_data
            }
        },
        {
            "type": "text", 
            "text": f"For your reference, the advertiser banner request is: {banner_request}"
        }
        ])
    ]

    try:
        response = llm.with_structured_output(BOutput).invoke(planning_messages).model_dump()
        response_ = {"score": response["score"], "explanation": response["explanation"]}
    except Exception as e:
        print(f"Error processing")
        print(e)
    print(response_)


if __name__ == "__main__":
    run(args.image_file, args.logo_file, args.banner_request)
