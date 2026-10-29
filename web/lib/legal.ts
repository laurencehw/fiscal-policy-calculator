import { AUTHOR_URL, CONTACT_EMAIL, REPO_URL } from "./site";

export function contactParagraphs(): string[] {
  return [
    `Email ${CONTACT_EMAIL}.`,
    "Laurence Wilse-Samson maintains the Fiscal Policy Calculator as a personal research project. Write about a score that looks wrong, a published figure the site should be checked against, a classroom assignment, or a correction to the methods. There is no comment form and no account. Email is the way in.",
    "The calculator estimates what a U.S. tax or spending proposal does to the federal deficit over ten years. It is not an official score from the Congressional Budget Office, the Joint Committee on Taxation, or the Treasury, and a reply to an email is not one either. If a number on the site disagrees with a document, name the page and the document.",
    `The source and the validation ledger are on GitHub at ${REPO_URL}. The author's site is ${AUTHOR_URL}. This project has no office and no postal address. It is not a business and it does not take payments.`,
  ];
}

export function contactText(): string {
  return ["Contact", ...contactParagraphs()].join(" ");
}

export function privacyParagraphs(): string[] {
  return [
    "The Fiscal Policy Calculator does not ask you to create an account, and it does not sell personal information. The pages are static estimates computed nightly from public budget data. Opening one is a request for a page.",
    "Ask is the exception. A question you submit on Ask is sent to Anthropic to answer and is not stored by this site. Anthropic's handling of that request is covered by Anthropic's own terms. Do not send secrets, account numbers, or anyone else's personal information in a question.",
    "The site keeps a daily cost cap and a per-visitor limit so the assistant cannot run without bound. Those counters are operational. They are not a profile, and they are not joined to your name, because the site never asks for one.",
    "Classroom saves progress in the browser on the computer you are using. Clearing that browser's storage clears it. The site does not receive a class roster.",
    "The host may record an address and a path for a short time, the way any host does, to keep the site up. Those logs are not used to build a marketing list. There is no advertising on the site.",
    `The author is Laurence Wilse-Samson, ${CONTACT_EMAIL}. This page is the whole privacy policy. There is no separate company and no postal address.`,
  ];
}

export function privacyText(): string {
  return ["Privacy", ...privacyParagraphs()].join(" ");
}
