import { AUTHOR_URL, CONTACT_EMAIL, REPO_URL } from "./site";

export function contactParagraphs(): string[] {
  return [
    `Email ${CONTACT_EMAIL}.`,
    "I maintain the Fiscal Policy Calculator as a personal research project. Please write if a score looks wrong, if there is a published figure the site should be checked against, or about a classroom assignment or a correction to the methods. There is no comment form and no account, so email is the only way to reach me.",
    "The calculator estimates what a U.S. tax or spending proposal does to the federal deficit over ten years. It is not an official score from the Congressional Budget Office, the Joint Committee on Taxation, or the Treasury, and a reply to an email is not one either. If a number on the site disagrees with a published document, it helps if you name both the page and the document.",
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
    "The site keeps a daily cost cap and a per-visitor limit so the assistant cannot run without bound. Those counters exist only to keep the site running. They do not build a profile and are not linked to your name, which the site never asks for.",
    "Classroom saves progress in the browser on the computer you are using. Clearing that browser's storage clears it. The site does not receive a class roster.",
    "The host may record an address and a path for a short time, the way any host does, to keep the site up. Those logs are not used to build a marketing list. There is no advertising on the site.",
    `The author is Laurence Wilse-Samson, ${CONTACT_EMAIL}. This page is the whole privacy policy. There is no separate company and no postal address.`,
  ];
}

export function privacyText(): string {
  return ["Privacy", ...privacyParagraphs()].join(" ");
}
