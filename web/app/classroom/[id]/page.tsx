import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { Classroom } from "@/components/Classroom";
import { classroomAssignment, classroomIndex } from "@/lib/data";

export const dynamicParams = false;

export function generateStaticParams() {
  return classroomIndex().map((row) => ({ id: row.id }));
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  const a = classroomAssignment(id);
  if (!a) return {};
  return { title: a.title, description: a.description, alternates: { canonical: `/classroom/${a.id}` } };
}

export default async function AssignmentPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const assignment = classroomAssignment(id);
  if (!assignment) notFound();
  return (
    <>
      <header>
        <span className="eyebrow noprint">
          <Link href="/classroom">Classroom</Link> · about {assignment.minutes} minutes
        </span>
        <h1>{assignment.title}</h1>
        <p className="sentence noprint">{assignment.description}</p>
        <details className="noprint">
          <summary>What you will learn</summary>
          <ul className="marked">
            {assignment.objectives.map((o) => (
              <li key={o}>{o}</li>
            ))}
          </ul>
        </details>
      </header>
      <Suspense>
        <Classroom assignment={assignment} />
      </Suspense>
    </>
  );
}
