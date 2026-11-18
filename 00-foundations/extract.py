from pydantic import BaseModel, ValidationError, field_validator

from aicore.llm import client


class ExperienceEntry(BaseModel):
    title: str
    company: str
    start_date: str | None = None
    end_date: str | None = None


class EducationEntry(BaseModel):
    degree: str
    institution: str
    start_date: str | None = None
    end_date: str | None = None


class ResumeData(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    summary: str | None = None
    skills: list[str] = []
    experience: list[ExperienceEntry] = []
    education: list[EducationEntry] = []
    most_recent_title: str | None = None

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name is blank — this input probably isn't a resume at all")
        return v


SAMPLE_RESUME = """
  Priya Sharma
  priya.sharma92@gmail.com | Bangalore, India | +91 98765 43210

  Backend engineer with about 5 yrs experience building scalable systems,
  mostly Java/Spring and some Python on the side. Enjoys mentoring juniors.

  EXPERIENCE

  Senior Software Engineer, Flipkart Internal Tools Team (Aug 2022 - Present)
  Built internal logistics dashboard serving 40k daily users, led migration
  of a monolith to microservices, cut deployment time from 2hrs to 12 mins.

  Software Engineer II - Razorpay, Bangalore
  June 2019 to July 2022
  Worked on payment reconciliation systems. Owned the settlement pipeline.
  Promoted once during this stint.

  Junior Developer @ a small startup (no longer exists) - roughly 2017-2019,
  general full stack work, mostly PHP honestly, wouldn't put too much
  weight on this one.

  EDUCATION
  B.Tech Computer Science, VIT Vellore, 2013-2017

  SKILLS: Java, Spring Boot, Python, PostgreSQL, Kafka, Docker, AWS, system design,
  also decent at Excel lol
  """


SAMPLE_RESUME_NO_EMAIL = """
  Priya Sharma
  Bangalore, India | +91 98765 43210

  Backend engineer with about 5 yrs experience building scalable systems,
  mostly Java/Spring and some Python on the side. Enjoys mentoring juniors.

  EXPERIENCE

  Senior Software Engineer, Flipkart Internal Tools Team (Aug 2022 - Present)
  Built internal logistics dashboard serving 40k daily users, led migration
  of a monolith to microservices, cut deployment time from 2hrs to 12 mins.

  Software Engineer II - Razorpay, Bangalore
  June 2019 to July 2022
  Worked on payment reconciliation systems. Owned the settlement pipeline.
  Promoted once during this stint.

  Junior Developer @ a small startup (no longer exists) - roughly 2017-2019,
  general full stack work, mostly PHP honestly, wouldn't put too much
  weight on this one.

  EDUCATION
  B.Tech Computer Science, VIT Vellore, 2013-2017

  SKILLS: Java, Spring Boot, Python, PostgreSQL, Kafka, Docker, AWS, system design,
  also decent at Excel lol
  """

NOT_A_RESUME = """
  Grocery list for Sunday:
  - 2kg rice, 1L milk, onions, tomatoes, dish soap
  - Pick up dry cleaning before 6pm
  - Call the electrician about the kitchen socket
  """


def extract_resume_data(resume_text: str) -> ResumeData:
    response = client().messages.parse(
        model="claude-opus-5",
        max_tokens=16000,
        messages=[
            {
                "role": "user",
                "content": f"Extract structured resume data from this text:\n\n{resume_text}",
            }
        ],
        output_format=ResumeData,
    )
    if response.parsed_output is None:
        raise RuntimeError("Failed to parse resume data from LLM response")
    return response.parsed_output


if __name__ == "__main__":
    try:
        resume = extract_resume_data(NOT_A_RESUME)
        print(resume.model_dump_json(indent=2))
    except ValidationError as e:
        print(f"Extraction failed — this probably isn't a real resume.\n{e}")
