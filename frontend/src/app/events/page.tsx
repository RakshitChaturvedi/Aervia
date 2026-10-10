import { redirect } from 'next/navigation';

export default function EventsPageRedirect() {
  redirect('/alerts');
}
