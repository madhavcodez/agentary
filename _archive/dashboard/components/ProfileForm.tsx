import type { Profile } from "@/lib/types";

interface ProfileFormProps {
  profile: Profile;
}

export default function ProfileForm({ profile }: ProfileFormProps) {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-full bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
            <span className="text-xl font-bold text-indigo-400">
              {profile.name?.charAt(0)?.toUpperCase() ?? "?"}
            </span>
          </div>
          <div>
            <h2 className="text-xl font-semibold text-gray-100">{profile.name}</h2>
            <div className="flex items-center gap-4 mt-1">
              {profile.email && (
                <span className="text-sm text-gray-400">{profile.email}</span>
              )}
              {profile.phone && (
                <span className="text-sm text-gray-400">{profile.phone}</span>
              )}
              {profile.location && (
                <span className="text-sm text-gray-400">{profile.location}</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Summary */}
      {profile.summary && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">
            Summary
          </h3>
          <p className="text-sm text-gray-400 leading-relaxed">{profile.summary}</p>
        </div>
      )}

      {/* Skills */}
      {profile.skills.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">
            Skills
          </h3>
          <div className="flex flex-wrap gap-2">
            {profile.skills.map((skill, idx) => (
              <span
                key={skill.id ?? idx}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-300 hover:border-indigo-500/30 hover:text-indigo-300 transition-colors"
              >
                <span>{skill.name}</span>
                {skill.proficiency && (
                  <span className="text-xs text-gray-500">({skill.proficiency})</span>
                )}
                {skill.years_experience && (
                  <span className="text-xs text-gray-600">{skill.years_experience}y</span>
                )}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Experience */}
      {profile.experiences.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">
            Experience
          </h3>
          <div className="relative">
            <div className="absolute left-3 top-2 bottom-2 w-px bg-gray-800" />
            <div className="space-y-6">
              {profile.experiences.map((exp, idx) => (
                <div key={exp.id ?? idx} className="relative pl-8">
                  <div className="absolute left-1.5 top-1.5 w-3 h-3 rounded-full bg-gray-800 border-2 border-indigo-500" />
                  <div>
                    <h4 className="text-sm font-semibold text-gray-200">{exp.title}</h4>
                    <p className="text-sm text-indigo-400">{exp.company}</p>
                    <div className="flex items-center gap-2 mt-1">
                      {exp.start_date && (
                        <span className="text-xs text-gray-500">
                          {exp.start_date}
                          {exp.end_date ? ` - ${exp.end_date}` : " - Present"}
                        </span>
                      )}
                    </div>
                    {exp.description && (
                      <p className="text-sm text-gray-400 mt-2 leading-relaxed">
                        {exp.description}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Preferences */}
      {profile.preferences.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">
            Preferences
          </h3>
          <div className="grid grid-cols-2 gap-3">
            {profile.preferences.map((pref, idx) => (
              <div
                key={pref.id ?? idx}
                className="bg-gray-800/50 border border-gray-700/50 rounded-lg px-4 py-3"
              >
                <span className="text-xs text-gray-500 uppercase tracking-wider">{pref.key}</span>
                <p className="text-sm text-gray-300 mt-0.5">{pref.value}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
