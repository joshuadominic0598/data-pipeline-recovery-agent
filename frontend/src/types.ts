export type Obj = Record<string, any>;
export type Run = Obj & {
  id: string;
  status: string;
  date: string;
  scenario: string;
  stages: Obj;
  events?: Obj[];
  emails?: Obj[];
};
